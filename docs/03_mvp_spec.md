# MVP仕様（v0.1 / WIP）
本MVPは「契約ルール判定（解約/停止/返金保証等）の判断支援」を目的とし、
AIによる最終判断の自動化は行わない。
オペレーターが根拠を確認し、適切に処理できる状態を最優先とする。

---

## 1. MVPのスコープ

### In Scope（MVPでやる）
- ナレッジ（Knowledge Unit）を検索して提示する
- “判断に必要な根拠”と“次アクション”を構造化して返す
- 例外（強い解約希望等）の候補を提示し、SV確認推奨を明示する
- ルールの版管理（version/effective_from/effective_to/source_refs）を保持し、適用候補を返す
- 信頼できない参照項目（例：定期お約束回数）に警告を出す

### Out of Scope（MVPではやらない）
- AIによる最終判断の自動化
- 顧客向け自動返信
- 決済/請求/会計処理の変更
- ECForceへの書き込み自動化（解約処理の自動実行等）
- 完全なUI整備（最小の検証用UIに留める）

---

## 2. 対象ユースケース（まず1つ）
- 解約希望：漲天 / 7回お約束コースLN（旧称：7回受け取りお約束コース）
- “縛り回数カウント”と“例外（強い解約希望）”を中心に検証する

---

## 3. 入力（オペレーターが与える情報）
MVPは「必要最小限の入力」を前提にする。

### 必須
- client_company_id（例：KN等）
- product_name（例：漲天）
- course_name（例：7回お約束コースLN）
- inquiry_type（例：解約希望）
- shipped_count（発送済み受注数・返品除外の結果）
- has_return_flow（返品/返金保証/CO/解約金請求中などの別フロー有無：true/false）
- next_ship_date（次回発送予定日）
- days_to_next_ship（次回発送予定日までの日数）

### 任意（あると精度が上がる）
- strong_cancel_intent（強い解約希望：true/false）
- keywords_flags（特定ワード検知：配列）
- memo_flags（顧客メモ由来の注意フラグ：配列）
- upsell_history（アップセル元コース名など）

---

## 4. 出力（JSON：判断支援として返す）
MVPは「結論」ではなく「根拠＋候補＋次アクション」を返す。

```json
{
  "case_summary": {
    "product_name": "漲天",
    "course_name": "7回お約束コースLN",
    "inquiry_type": "解約希望"
  },
  "recommendations": [
    {
      "label": "原則ルール",
      "result": "解約可/不可/条件付き",
      "reason": "要点",
      "knowledge_refs": [
        {
          "know_id": "KU-02...",
          "version": "v1",
          "effective_from": "YYYY-MM-DD",
          "effective_to": null,
          "source_refs": ["spreadsheet:...", "minutes:...", "chatwork:..."]
        }
      ],
      "next_actions": ["確認すべき画面", "送るべきテンプレ", "SVへ確認"]
    }
  ],
  "warnings": [
    {
      "type": "data_reliability",
      "message": "定期お約束回数は設定ミスが多く判断根拠にしない"
    },
    {
      "type": "missing_source",
      "message": "根拠が未添付のナレッジが含まれるためSV確認推奨"
    }
  ],
  "operator_checklist": [
    "発送済み受注数（返品除外）を確認",
    "別フロー中でないか確認",
    "次回発送予定日が期限内か確認",
    "温度感/特定ワードの有無を確認"
  ]
}
