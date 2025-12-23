# API Contract（入出力仕様）v0.1 / WIP

本ドキュメントは、契約ルール判断支援MVPにおけるAPIの入出力（Contract）を定義する。
本MVPは「結論の自動化」ではなく、「判断支援（根拠・警告・次アクション提示）」を目的とする。

## 関連ドキュメント
- docs/03_mvp_spec.md（MVP仕様）
- docs/04_knowledge_schema.md（ナレッジスキーマ）
- docs/08_csv_export_spec.md（CSVエクスポート仕様）
- docs/02_knowledge_units/KU-00_versioning_policy.md（版管理ポリシー）

---

## 1. 共通方針

### 1.1 APIの役割
- APIは **最終判断を行わない**
- 判断に必要な「候補・根拠・警告・次アクション」を返す
- 不確実性がある場合は warnings で必ず明示する

### 1.2 ナレッジ選定ルール
- 主キー：client_company_id / product_name / course_name
- version / effective_from / effective_to を考慮して適用候補を抽出
- status=approved を優先する
- status=draft が含まれる場合は warnings を返す

---

## 2. API一覧

| Endpoint | Method | 目的 |
|---|---|---|
| /health | GET | 稼働確認 |
| /search | POST | ナレッジ検索（Knowledge Unit候補一覧） |
| /answer_decision | POST | ケース入力に対する判断支援 |

---

## 3. /health

### Request
なし

### Response（例）

{
  "status": "ok"
}

---

## 4. /search（ナレッジ検索）

### 4.1 Request（JSON）

{
  "query": "縛り回数 返品除外",
  "top_k": 5,
  "filters": {
    "client_company_id": "KN",
    "product_name": "漲天",
    "course_name": "7回お約束コースLN",
    "rule_type": ["RULE", "EXCEPTION", "RELIABILITY"],
    "status": ["approved", "draft"]
  }
}

### フィールド説明

- query（必須）：全文検索クエリ
- top_k（任意）：返却件数（デフォルト5）
- filters（任意）：条件指定

### 4.2 Response（JSON）

{
  "results": [
    {
      "know_id": "KU-02-001",
      "client_company_id": "KN",
      "product_name": "漲天",
      "course_name": "7回お約束コースLN",
      "course_alias": "7回受け取りお約束コース",
      "rule_type": "RULE",
      "status": "draft",
      "priority": "P1",
      "version": "v1",
      "effective_from": "2025-12-23",
      "effective_to": null,
      "summary": "縛り回数は発送済み受注数（返品除外）で判定する",
      "body": "・・・",
      "tags": ["解約", "縛り", "返品除外"],
      "source_refs": [
        "spreadsheet: ...",
        "minutes: ...",
        "chatwork: ..."
      ],
      "score": 0.78
    }
  ]
}

---

## 5. /answer_decision（判断支援）

### 5.1 Request（JSON）

{
  "case": {
    "client_company_id": "KN",
    "product_name": "漲天",
    "course_name": "7回お約束コースLN",
    "inquiry_type": "解約希望",

    "shipped_count": 7,
    "has_return_flow": false,
    "next_ship_date": "2025-12-25",
    "days_to_next_ship": 2,

    "strong_cancel_intent": false,
    "keywords_flags": [],
    "memo_flags": []
  },
  "top_k": 8
}

### caseフィールド補足

- shipped_count：発送済み受注数（返品除外済み）
- has_return_flow：別フロー（返品/返金保証/CO/解約金請求中 等）
- days_to_next_ship：次回発送までの日数
- strong_cancel_intent：強い解約希望（暫定は手入力）

### 5.2 Response（JSON）

{
  "case_summary": {
    "client_company_id": "KN",
    "product_name": "漲天",
    "course_name": "7回お約束コースLN",
    "inquiry_type": "解約希望"
  },
  "recommendations": [
    {
      "label": "原則ルール",
      "result": "解約可/不可/条件付き",
      "reason": "発送済み受注数（返品除外）を基準に判定",
      "knowledge_refs": [
        {
          "know_id": "KU-02-001",
          "rule_type": "RULE",
          "status": "draft",
          "version": "v1",
          "effective_from": "2025-12-23",
          "effective_to": null,
          "source_refs": [
            "spreadsheet: ...",
            "minutes: ...",
            "chatwork: ..."
          ]
        }
      ],
      "next_actions": [
        "発送済み受注数を再確認（返品除外）",
        "別フロー中でないか確認"
      ]
    },
    {
      "label": "例外候補",
      "result": "SV確認推奨",
      "reason": "強い解約希望に該当する可能性",
      "knowledge_refs": [
        {
          "know_id": "KU-05-001",
          "rule_type": "EXCEPTION",
          "status": "draft",
          "version": "v1",
          "effective_from": "2025-12-23",
          "effective_to": null,
          "source_refs": [
            "spreadsheet: ...",
            "minutes: ...",
            "chatwork: ..."
          ]
        }
      ],
      "next_actions": [
        "再問い合わせの有無を確認",
        "温度感（クレーム化リスク）を確認",
        "解約金条件（8000円 / 4990円）を確認"
      ]
    }
  ],
  "warnings": [
    {
      "type": "data_reliability",
      "message": "定期お約束回数は設定ミスがあるため判断根拠にしない",
      "related_to": "KU-02-001"
    },
    {
      "type": "draft_knowledge_used",
      "message": "status=draft のナレッジが含まれるため承認確認推奨",
      "related_to": "KU-02-001"
    },
    {
      "type": "sv_confirmation_recommended",
      "message": "例外対応の可能性があるためSV確認推奨",
      "related_to": "KU-05-001"
    }
  ],
  "operator_checklist": [
    "発送済み受注数（返品除外）を確認",
    "別フロー中でないか確認",
    "次回発送予定日と期限を確認",
    "温度感・特定ワードの有無を確認"
  ]
}

---

## 6. warnings 種別一覧

| type                        | 説明              |
| --------------------------- | --------------- |
| data_reliability            | 信頼できないデータが判断に影響 |
| missing_source_refs         | 根拠不足            |
| draft_knowledge_used        | draftナレッジ使用     |
| version_ambiguity           | 適用期間が曖昧         |
| sv_confirmation_recommended | SV確認推奨          |

---

## 7. 将来拡張

- strong_cancel_intent の自動判定支援
- status=approved のみを返すモード
- course_alias / tags を使った検索精度改善

---