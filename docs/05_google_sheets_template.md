# Google Sheets テンプレ（Knowledge Unit 管理）v0.1 / WIP

本シートは `04_knowledge_schema.md` に準拠し、ナレッジ（Knowledge Unit / KU）を
Google Sheetsで登録・改定・承認できるようにするためのテンプレである。

---

## 1. シート構成（推奨）

- Sheet: `knowledge_units`
  - KUの本体（1行=1KU）
- Sheet: `code_master`（任意）
  - rule_type / status などのコード表（データ検証に使用）
- Sheet: `change_log`（任意）
  - 重要な変更の記録（decision_log と併用）

---

## 2. knowledge_units 列定義（この順で作成推奨）

### A. 識別・対象
| 列 | カラム名 | 必須 | 型/例 | 説明 |
|---|---|---|---|---|
| A | know_id | ○ | `KU-02-001` / UUID | 一意ID（変更しても固定） |
| B | client_company_id | ○ | `KN` / `URBAN` 等 | クライアント識別 |
| C | product_name | ○ | `漲天` | 商材名 |
| D | course_name | ○ | `7回お約束コースLN` | 正式コース名 |
| E | course_alias | | `7回受け取りお約束コース` | 旧称/別名（検索用） |

### B. 分類・状態
| 列 | カラム名 | 必須 | 型/例 | 説明 |
|---|---|---|---|---|
| F | rule_type | ○ | `RULE` | RULE/EXCEPTION/PROCEDURE/RELIABILITY |
| G | status | ○ | `draft` | draft/approved/deprecated |
| H | priority | | `P1` | P0/P1/P2（任意：重要度） |

### C. 版管理（versioning）
| 列 | カラム名 | 必須 | 型/例 | 説明 |
|---|---|---|---|---|
| I | version | ○ | `v1` | 上書き禁止。改定時はv2,v3… |
| J | effective_from | ○ | `2025-12-01` | 適用開始日（YYYY-MM-DD） |
| K | effective_to | | `2026-03-31` | 適用終了日（なければ空） |
| L | supersedes_know_id | | `KU-02-000` | 置換元KU（任意） |

### D. 内容（検索と根拠）
| 列 | カラム名 | 必須 | 型/例 | 説明 |
|---|---|---|---|---|
| M | summary | ○ | `縛り回数は発送済み（返品除外）で判定` | 1〜2行要約（検索ヒットの核） |
| N | body | ○ | （長文OK） | 詳細本文（判断・根拠・手順） |
| O | tags | | `解約,縛り,アップセル,返品除外` | カンマ区切り |
| P | source_refs | ○ | 下の形式 | 根拠（複数可）。口頭は禁止 |

### E. 運用メタ
| 列 | カラム名 | 必須 | 型/例 | 説明 |
|---|---|---|---|---|
| Q | owner | | `SV_山田` | 主担当（任意） |
| R | reviewer | | `管理者_佐藤` | 承認者（approved時に記入） |
| S | approved_at | | `2025-12-23` | 承認日 |
| T | notes | | `事故防止：定期お約束回数は信用しない` | 補足 |

---

## 3. 入力ルール（重要）

### 3.1 上書き禁止（version運用）
- ルール変更時は **行を複製して新行を作る**
- `version` を上げる（v1→v2）
- 旧行の `effective_to` を埋める（終了日）
- `status` は旧行を `deprecated` にしても良い（運用に合わせる）

### 3.2 source_refs 記述ルール（必須）
複数可。以下の形式で記載：

- spreadsheet: ファイル名 / シート名 / 行 or セル
- minutes: 会議日付 / 議題 / 該当箇所
- chatwork: ルーム名 / 日付 / 検索語 or メッセージURL

例：
spreadsheet: 商材一覧 / 解約条件 / 行23
minutes: 2025-12-10 定例会 / 解約条件確認 / 3項
chatwork: CS運用 / 2025-12-11 / 「縛り回数 返品除外」

※「口頭」「覚えている人」は禁止（必ずソース化する）

---

## 4. データ検証（Google Sheets の設定案）

### rule_type（F列）
- ドロップダウン：`RULE,EXCEPTION,PROCEDURE,RELIABILITY`

### status（G列）
- ドロップダウン：`draft,approved,deprecated`

### effective_from / effective_to（J/K列）
- 日付形式（YYYY-MM-DD）
- 可能なら「日付であること」を検証

### 必須チェック（おすすめ運用）
- `know_id, client_company_id, product_name, course_name, rule_type, status, version, effective_from, summary, body, source_refs`
  が空なら承認しない（status=approvedにしない）

---

## 5. 記入例（KU-02：縛り回数）

know_id: KU-02-001
client_company_id: KN
product_name: 漲天
course_name: 7回お約束コースLN
course_alias: 7回受け取りお約束コース
rule_type: RULE
status: approved
version: v1
effective_from: 2025-12-01
summary: 縛り回数は発送済み受注数（返品除外）で判定する
body: 縛り回数は「発送済み受注数」をカウントし、返品受注は含めない。定期受注管理の「定期お約束回数」は設定ミスがあるため判断根拠にしない。
tags: 解約,縛り,発送回数,返品除外,信頼性
source_refs:
- spreadsheet: 商材一覧 / 解約条件 / 行23
- minutes: 2025-12-10 定例会 / 解約条件確認 / 3項
- chatwork: CS運用 / 2025-12-11 / 「縛り回数 返品除外」
owner: 業務管理者
reviewer: SV
approved_at: 2025-12-23
notes: 事故防止：返品混入で発送回数を誤認しやすい
