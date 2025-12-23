# CSVエクスポート仕様（v0.1 / WIP）

本ドキュメントは、Google Sheets（knowledge_units）で管理しているKnowledge Unit（KU）を
RAG投入用CSVとしてエクスポートする際の仕様を定義する。

---

## 1. 目的
- knowledge_units の内容を、機械処理しやすいCSVに変換する
- 後任者が同じ手順で再現できるよう、列・整形ルールを固定する

---

## 2. 前提
- Google Sheetsのヘッダは「英名（和名）」形式を許容する（例：know_id（ナレッジID））
- CSVのヘッダは **英名のみ** を正とする（例：know_id）

---

## 3. 出力CSVのファイル名（推奨）
- knowledge_units_export_YYYYMMDD.csv
- サンプルは docs/08_samples/knowledge_units_sample.csv とする

---

## 4. CSVの列（MVP）
MVPでは以下の列を出力する（順番固定推奨）。

| 列名（英名） | 必須 | 例 | 備考 |
|---|---|---|---|
| know_id | ○ | KU-02-001 | |
| client_company_id | ○ | KN | |
| product_name | ○ | 漲天 | |
| course_name | ○ | 7回お約束コースLN | |
| course_alias | | 7回受け取りお約束コース | |
| rule_type | ○ | RULE | |
| status | ○ | draft | approved のみを出す運用も可 |
| priority | | P1 | |
| version | ○ | v1 | |
| effective_from | ○ | 2025-12-23 | |
| effective_to | |  | |
| summary | ○ | ... | |
| body | ○ | ... | |
| tags | | ... | カンマ区切り |
| source_refs | ○ | ... | 複数は `;` 区切り推奨 |
| owner | | ... | |
| reviewer | | ... | |
| approved_at | | ... | |
| notes | | ... | |

---

## 5. ヘッダ正規化ルール（重要）
Google Sheetsのヘッダが `英名（和名）` の場合、
CSVヘッダは `（` より前だけを採用する。

例：
- `know_id（ナレッジID）` → `know_id`
- `effective_from（適用開始日）` → `effective_from`

---

## 6. テキスト整形ルール
- 改行：CSV内では改行を保持してよいが、ツールによって崩れる場合は `\n` に置換する
- source_refs：複数根拠は `;` 区切りに統一する（例：`spreadsheet:...; minutes:...; chatwork:...`）
- tags：カンマ区切り（例：`解約,縛り,返品除外`）

---

## 7. フィルタリング（推奨）
- MVP段階は `status=approved` のみ出力する運用が安全
- 検証中は `draft` も含めてよい（ただし返答側で警告を出す）

---

## 8. サンプル
- docs/08_samples/knowledge_units_sample.csv に KU-02/KU-05 の例を添付する
