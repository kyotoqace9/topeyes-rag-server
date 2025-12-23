# Knowledge Schema（ナレッジ登録フォーマット）v0.1 / WIP

本ドキュメントは、契約ルール・例外・業務判断に関するナレッジを
「蓄積・検索・改定」可能にするための共通フォーマットを定義する。

本スキーマは、Google Sheets / CSV / RAG / DB のいずれでも共通で使用する。

---

## 1. 基本方針

- ナレッジは「1件 = 1 Knowledge Unit（KU）」とする
- 上書きは禁止し、変更時は version を上げる
- 根拠（source_refs）がないナレッジは暫定扱いとする
- 人の記憶だけに依存する情報は禁止する

---

## 2. 必須カラム（MVP）

- 英名（snake_case）は機械処理の正とする
- Google Sheetsのヘッダは「英名（和名）」で併記してよい
- エクスポート/連携時は「（」より前の英名をキーとして扱う

| カラム名 | 必須 | 説明 |
|--------|------|------|
| know_id（ナレッジID） | ○ | ナレッジ一意ID（UUID等） |
| client_company_id（クライアントID） | ○ | クライアント識別 |
| product_name（商材名） | ○ | 商材名（例：漲天） |
| course_name（コース名） | ○ | コース名（例：7回お約束コースLN） |
| rule_type（種別） | ○ | RULE / EXCEPTION / PROCEDURE / RELIABILITY |
| version（版） | ○ | v1, v2 ... |
| effective_from（適用開始日） | ○ | 適用開始日 |
| effective_to（適用終了日） |  | 適用終了日（なければ空） |
| summary（要約） | ○ | 検索用要約（1〜2行） |
| body（本文） | ○ | 詳細ルール本文 |
| source_refs（根拠） | ○ | 根拠（スプシ/議事録/Chatwork等） |
| tags（タグ） |  | 検索用タグ（カンマ区切り） |
| status（状態） | ○ | draft / approved / deprecated |


---

## 3. rule_type 定義

### RULE
- 原則ルール（例：縛り達成前は解約不可）

### EXCEPTION
- 例外条件（例：強い解約希望、解約金条件）

### PROCEDURE
- 業務手順（画面操作・確認手順）

### RELIABILITY
- 信頼できない項目・注意喚起
  - 例：定期お約束回数は信用しない

---

## 4. source_refs 記述ルール（必須）

複数可。以下の形式で記載する。

- spreadsheet: ファイル名 / シート名 / 行 or セル
- minutes: 会議日付 / 議題 / 該当箇所
- chatwork: ルーム名 / 日付 / 検索語 or メッセージURL

※ 「口頭」「覚えている人」は禁止

---

## 5. 版管理ルール（要約）

- 変更時は version を上げる
- 旧版には effective_to を必ず入れる
- decision_log に変更理由を記録する

---

## 6. MVPでの最小運用

- 最初は approved / draft の2状態でよい
- source_refs が無い場合は draft 扱い
- 返答時に「根拠未添付」の警告を出す

---

## 7. 記入例（KU-02 抜粋）

know_id: KU-02-001  
product_name: 漲天  
course_name: 7回お約束コースLN  
rule_type: RULE  
version: v1  
effective_from: 2023-01-01  
summary: 縛り回数は発送済み受注数（返品除外）で判定する  
body: 縛り回数は…  
source_refs:
- spreadsheet: 商材一覧 / 解約条件 / 行23
- minutes: 2023-02-10 定例会 / 解約条件確認
- chatwork: CS運用 / 2023-02 / 「縛り回数」
status: approved
