import os
from typing import Optional, List, Dict, Any

import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from sentence_transformers import SentenceTransformer

import re

from fastapi.middleware.cors import CORSMiddleware

# =========================
# Config (環境変数で上書き可)
# =========================
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
COLLECTION = os.getenv("QDRANT_COLLECTION", "rag_contract_rules_mvp")
EMBED_MODEL = os.getenv("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:1b")  # 例。手元のモデル名に合わせて変更

DEFAULT_TOP_K = int(os.getenv("TOP_K", "5"))

COMMON_COURSE_ID = "COMMON"


# =========================
# App init
# =========================
app = FastAPI(title="Thin RAG Server", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # まずは検証用に全許可。運用ではURL指定推奨
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

qdrant = QdrantClient(url=QDRANT_URL)
embedder = SentenceTransformer(EMBED_MODEL)


# =========================
# Schemas
# =========================
class SearchRequest(BaseModel):
    query: str = Field(..., description="ユーザーの質問文")
    top_k: int = Field(DEFAULT_TOP_K, ge=1, le=20)
    course_id: Optional[str] = Field(None, description="例: DP_7P_001 / DP_BM_001 / DP_OMJ_001。指定すると絞り込み検索")
    category: Optional[str] = Field(None, description="例: 解約期限 / 縛り・解約金 / 返金保証 / 返品・返金原則")


class SearchHit(BaseModel):
    score: float
    payload: Dict[str, Any]


class SearchResponse(BaseModel):
    collection: str
    top_k: int
    hits: List[SearchHit]


class AnswerRequest(BaseModel):
    query: str
    top_k: int = Field(DEFAULT_TOP_K, ge=1, le=20)
    course_id: Optional[str] = None
    category: Optional[str] = None
    # 例: お問い合わせ画面/CS画面で得た事実を足す（任意）
    context: Optional[str] = Field(None, description="任意。顧客状況や受注回数、次回発送予定日などの補足")


class AnswerResponse(BaseModel):
    answer: str
    used_know_ids: List[str]
    hits: List[SearchHit]


class DecisionResponse(BaseModel):
    # 機械分岐用（Phase1）
    decision_code: str

    # 例: "初回のみの途中解約（例外）"
    decision: str

    # 解約金
    fee_required: bool
    fee_note: Optional[str] = None  # "初回解約金（所定額/別途確認）" など

    # 最終特例（免除など）
    exception_possible: bool
    exception_note: Optional[str] = None

    # 解約期限（見つかったら）
    deadline_rule: Optional[str] = None

    # オペレータが取るべき行動（短い箇条書き）
    operator_actions: List[str] = []

    # 判断に不足している情報
    needs_confirmation: List[str] = []

    # テンプレ合成（Phase1）
    customer_message: str
    operator_note: str
    operator_steps: List[str] = []
    decision_summary: Dict[str, Any]

    # 参照
    used_know_ids: List[str] = []
    hits: List[SearchHit] = []


# =========================
# Helpers (RAG)
# =========================
def build_filter(course_id: Optional[str], category: Optional[str]) -> Optional[qmodels.Filter]:
    must = []
    if course_id:
        must.append(
            qmodels.FieldCondition(
                key="course_id",
                match=qmodels.MatchValue(value=course_id),
            )
        )
    if category:
        must.append(
            qmodels.FieldCondition(
                key="category",
                match=qmodels.MatchValue(value=category),
            )
        )
    return qmodels.Filter(must=must) if must else None


def rag_search_single(query: str, top_k: int, course_id: Optional[str], category: Optional[str]) -> List[SearchHit]:
    vec = embedder.encode([query])[0].tolist()
    qfilter = build_filter(course_id, category)

    res = qdrant.query_points(
        collection_name=COLLECTION,
        query=vec,
        limit=top_k,
        with_payload=True,
        query_filter=qfilter,
    )

    points = res.points if hasattr(res, "points") else res
    hits: List[SearchHit] = []
    for p in points:
        payload = getattr(p, "payload", None) or {}
        score = float(getattr(p, "score", 0.0))
        hits.append(SearchHit(score=score, payload=payload))
    return hits


def _dedup_hits_by_know_id(hits: List[SearchHit]) -> List[SearchHit]:
    seen = set()
    merged: List[SearchHit] = []
    for h in hits:
        pl = h.payload or {}
        know_id = str(pl.get("know_id") or "").strip()
        key = know_id if know_id else str(pl.get("id") or "")  # 念のため
        if not key:
            # keyが取れないものは一旦入れてしまう（MVP）
            merged.append(h)
            continue
        if key in seen:
            continue
        seen.add(key)
        merged.append(h)
    return merged


def rag_search(query: str, top_k: int, course_id: Optional[str], category: Optional[str]) -> List[SearchHit]:
    """
    Phase1:
      - course_id が指定されている場合は、course_id + COMMON を両方検索してマージ
      - course_id が未指定なら、従来どおり（=全体検索）
    """
    if course_id and course_id != COMMON_COURSE_ID:
        hits_course = rag_search_single(query, top_k, course_id, category)
        hits_common = rag_search_single(query, top_k, COMMON_COURSE_ID, category)
        merged = _dedup_hits_by_know_id(hits_course + hits_common)
        merged.sort(key=lambda x: x.score, reverse=True)
        return merged[:top_k]
    else:
        return rag_search_single(query, top_k, course_id, category)


# =========================
# Helpers (Decision + Templates)
# =========================
def decide_code(result: Dict[str, Any]) -> str:
    # 優先度：確認が必要なら最優先
    if result.get("needs_confirmation"):
        return "NEED_CONFIRMATION"
    if result.get("fee_required") is True:
        return "ALLOW_WITH_FEE"
    if result.get("exception_possible") is True:
        return "ALLOW_EXCEPTION"

    decision_text = (result.get("decision") or "")
    if any(k in decision_text for k in ["不可", "できない", "受付できません", "原則は途中解約不可", "原則解約不可"]):
        return "DENY"
    return "ALLOW"

def summarize_for_ui(result: Dict[str, Any]) -> Dict[str, Any]:
    code = result.get("decision_code", "")
    decision = result.get("decision") or ""
    fee_required = result.get("fee_required")
    fee_note = (result.get("fee_note") or "").strip()
    exception_possible = bool(result.get("exception_possible"))
    deadline_known = bool(result.get("deadline_rule"))
    needs_confirmation = bool(result.get("needs_confirmation"))

    # can_cancel: DENY以外は基本 true 扱い（例外的に可/条件付き可も true）
    # ただし decision 文面に明確な「不可のみ」ニュアンスが強い場合は DENY に寄せる
    if code == "DENY":
        can_cancel = False
    else:
        can_cancel = True

    # fee_status
    # - fee_required True → REQUIRED
    # - fee_required False かつ「解約金なし」が明記 → NONE
    # - それ以外 → UNKNOWN
    if fee_required is True:
        fee_status = "REQUIRED"
    elif fee_required is False:
        if "解約金なし" in fee_note or "なし" in fee_note:
            fee_status = "NONE"
        else:
            # fee_required False でも情報が曖昧なら UNKNOWN に寄せる（安全側）
            fee_status = "UNKNOWN"
    else:
        fee_status = "UNKNOWN"

    # 例外があるか（最終特例含む）
    exception_available = exception_possible

    return {
        "can_cancel": can_cancel,
        "fee_status": fee_status,
        "exception_available": exception_available,
        "deadline_known": deadline_known,
        "needs_confirmation": needs_confirmation,
        # UIで使いたければ表示用の短い補足もここに足せる
        "decision_code": code,
    }


def render_templates(query: str, context: Optional[str], result: Dict[str, Any]) -> Dict[str, Any]:
    code = result.get("decision_code", "")
    decision = result.get("decision", "")
    fee_note = result.get("fee_note", "")
    exception_note = result.get("exception_note", "")
    deadline_rule = result.get("deadline_rule", "")
    needs = result.get("needs_confirmation", []) or []
    actions = result.get("operator_actions", []) or []
    used = result.get("used_know_ids", []) or []
    ctx = context or ""

    # 1) 顧客案内文（安全に、短く）
    parts: List[str] = []
    parts.append("お問い合わせありがとうございます。")
    if ctx:
        parts.append(f"状況を確認したところ、{ctx}")
    parts.append(decision)

    if code == "ALLOW_WITH_FEE" and fee_note:
        parts.append(f"なお、解約金については「{fee_note}」となります。")
    if code == "ALLOW_EXCEPTION" and exception_note:
        parts.append(f"また、例外対応の可能性については「{exception_note}」となります。")
    if deadline_rule:
        parts.append(f"受付期限の目安：{deadline_rule}")

    if needs:
        parts.append("確認が必要な点がございます：")
        parts.extend([f"・{n}" for n in needs])

    customer_message = "\n".join(parts)

    # 2) 社内メモ（根拠追跡）
    note_lines: List[str] = []
    note_lines.append(f"[受付内容] {query}")
    if ctx:
        note_lines.append(f"[状況] {ctx}")
    note_lines.append(f"[判断] {result.get('decision_code','')} / {decision}")
    if fee_note:
        note_lines.append(f"[解約金メモ] {fee_note}")
    if exception_note:
        note_lines.append(f"[例外メモ] {exception_note}")
    if deadline_rule:
        note_lines.append(f"[期限ルール] {deadline_rule}")
    if needs:
        note_lines.append("[要確認]")
        note_lines.extend([f"- {n}" for n in needs])
    note_lines.append(f"[根拠know_id] {', '.join(used) if used else '(なし)'}")

    operator_note = "\n".join(note_lines)

    # 3) オペ手順（見やすく番号）
    operator_steps = [f"{i+1}. {a}" for i, a in enumerate(actions)] if actions else []

    return {
        "customer_message": customer_message,
        "operator_note": operator_note,
        "operator_steps": operator_steps,
    }


def build_decision(query: str, context: Optional[str], hits: List[SearchHit]) -> Dict[str, Any]:
    """
    LLMを使わず、ルール文から機械的に判断JSONを組み立てる。
    まずはMVP用の素朴な実装（ルール文のキーワードに依存）。
    """
    used_ids = []
    texts = []
    for h in hits:
        pl = h.payload or {}
        used_ids.append(str(pl.get("know_id", "")))
        texts.append(str(pl.get("text", "")))

    all_text = "\n".join(texts)

    # ---- fee rules ----
    fee_required = False
    fee_note = None

    if ("初回解約金" in all_text) and ("条件に解約可" in all_text or "支払いを条件" in all_text):
        fee_required = True
        fee_note = "初回解約金（所定額／金額は別途確認）"
    elif ("二回目解約金" in all_text) and ("条件に解約可" in all_text or "支払いを条件" in all_text):
        fee_required = True
        fee_note = "二回目解約金（所定額／金額は別途確認）"
    elif ("解約金なし" in all_text) and ("解約可" in all_text):
        fee_required = False
        fee_note = "解約金なし（該当条件の場合）"

    # ---- exception rules ----
    exception_possible = False
    exception_note = None
    if ("どうしてもご納得いただけない" in all_text) and ("解約金なし" in all_text):
        exception_possible = True
        exception_note = "解約金の支払いに納得いただけない場合、最終特例として解約金なしで解約を承れる可能性あり（例外運用）"

    # ---- deadline ----
    deadline_rule = None
    if "解約受付期限" in all_text:
        m = re.search(r"(初回.*?解約受付期限.*?。)", all_text)
        if m:
            deadline_rule = m.group(1)
        else:
            m2 = re.search(r"(解約受付期限.*?。)", all_text)
            if m2:
                deadline_rule = m2.group(1)

    # ---- decision text ----
    decision = "ルールに基づき判断"
    ctx = context or ""
    if "受注回数=初回" in ctx or "受注回数=初回のみ" in ctx or "初回のみ" in ctx:
        if "原則として" in all_text and "解約は不可" in all_text:
            if fee_required:
                decision = "原則は途中解約不可。ただし強い解約希望がある場合、初回解約金（所定額）を条件に例外的に解約可。"
            else:
                decision = "原則は途中解約不可。ただし強い解約希望がある場合の例外ルールあり（条件確認）。"
        else:
            decision = "初回のみの解約希望：ルールに従い解約金条件などを確認して判断。"
    else:
        decision = "受注回数などの条件が不足しているため、ルール適用条件を確認して判断。"

    # ---- operator actions ----
    actions = []
    actions.append("コース/契約条件（縛りの有無）を案内する")
    if fee_required:
        actions.append("所定の解約金が発生する可能性を案内し、金額は別途確認する")
    if exception_possible:
        actions.append("解約金に納得不可の場合は最終特例（免除可否）を検討し、運用方針に従い判断する")
    if deadline_rule:
        actions.append("解約受付期限に該当するか（次回発送予定日基準）を確認する")
    actions.append("処理後に顧客メモへ根拠（know_id）と対応内容を記録する")

    # ---- needs confirmation ----
    needs = []
    if not any(k in ctx for k in ["受注回数=", "受注回数"]):
        needs.append("受注回数（初回のみ／2回目まで／3回目以降）")
    if ("次回発送予定日" not in ctx) and ("次回発送" not in ctx):
        needs.append("次回発送予定日（解約期限判定に必要）")
    if fee_required:
        needs.append("初回解約金の金額（所定額：マスター/別資料で確認）")

    result = {
        "decision": decision,
        "fee_required": fee_required,
        "fee_note": fee_note,
        "exception_possible": exception_possible,
        "exception_note": exception_note,
        "deadline_rule": deadline_rule,
        "operator_actions": actions,
        "needs_confirmation": needs,
        "used_know_ids": used_ids,
        "hits": hits,
    }
    return result


# =========================
# Prompt / Ollama
# =========================
def build_prompt(query: str, context: Optional[str], hits: List[SearchHit]) -> str:
    refs = []
    for h in hits:
        pl = h.payload
        refs.append(
            {
                "know_id": str(pl.get("know_id", "")),
                "course_id": str(pl.get("course_id", "")),
                "category": str(pl.get("category", "")),
                "title": str(pl.get("title", "")),
                "text": str(pl.get("text", "")),
            }
        )

    context_block = context or "（なし）"

    return f"""
あなたはコールセンターの解約対応の実務アシスタントです。
以下の【ルール】だけを根拠にして、【問い合わせ】への対応方針を日本語で回答してください。
推測で断言しないこと。ルールに金額が書かれていない場合は「解約金は発生する可能性がある（所定額）」までに留め、金額は「別途確認」と言うこと。

# 出力フォーマット（必ずこの順で）
【結論】（1〜3行）
【根拠】（know_id付きで箇条書き。最大3点）
【対応手順】（オペレータがやる操作/案内。箇条書き）
【追加で確認すべき事項】（不足情報がある場合のみ。箇条書き）
【参照know_id】（カンマ区切りで列挙）

# 追加コンテキスト
{context_block}

# 問い合わせ
{query}

# ルール（根拠データ）
{refs}
""".strip()


def ollama_generate(prompt: str) -> str:
    url = f"{OLLAMA_URL}/api/generate"
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
    }
    r = requests.post(url, json=payload, timeout=120)
    if r.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Ollama error {r.status_code}: {r.text}")
    data = r.json()
    return data.get("response", "")


# =========================
# Routes
# =========================
@app.get("/health")
def health():
    return {
        "status": "ok",
        "qdrant_url": QDRANT_URL,
        "collection": COLLECTION,
        "embed_model": EMBED_MODEL,
        "ollama_url": OLLAMA_URL,
        "ollama_model": OLLAMA_MODEL,
    }


@app.post("/search", response_model=SearchResponse)
def search(req: SearchRequest):
    try:
        hits = rag_search(req.query, req.top_k, req.course_id, req.category)
        return SearchResponse(collection=COLLECTION, top_k=req.top_k, hits=hits)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/answer", response_model=AnswerResponse)
def answer(req: AnswerRequest):
    try:
        hits = rag_search(req.query, req.top_k, req.course_id, req.category)

        prompt = build_prompt(req.query, req.context, hits)
        ans = ollama_generate(prompt)

        used_ids = [str(h.payload.get("know_id", "")) for h in hits]
        return AnswerResponse(answer=ans, used_know_ids=used_ids, hits=hits)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/answer_decision", response_model=DecisionResponse)
def answer_decision(req: AnswerRequest):
    try:
        hits = rag_search(req.query, req.top_k, req.course_id, req.category)

        base = build_decision(req.query, req.context, hits)
        base["decision_code"] = decide_code(base)
        base["decision_summary"] = summarize_for_ui(base)   # ←追加
        base.update(render_templates(req.query, req.context, base))

        # DecisionResponseに合う形で返す（dictでもOK）
        return base
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
