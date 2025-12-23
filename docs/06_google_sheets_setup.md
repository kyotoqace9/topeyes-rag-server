# Google Sheets 実シート設計（v0.1 / WIP）

本ドキュメントは、Knowledge Unit 管理用の Google Sheets を
誰が作っても同じ構成・同じ運用になるように定義する。

---

## 1. スプレッドシート全体構成

### 推奨ファイル名

knowledge_units_master


### シート一覧
| シート名 | 役割 |
|--------|------|
| knowledge_units | ナレッジ本体（1行 = 1 KU） |
| code_master | コード管理（rule_type / status 等） |
| change_log | 重要な変更・判断の履歴 |
| _meta | シート説明・注意書き（任意） |

---

## 2. knowledge_units シート

### 行・列ルール
- 1行目：ヘッダ（固定）
- 2行目以降：データ
- 1行 = 1 Knowledge Unit（KU）
- knowledge_units のヘッダ行は 英名（和名） で作る
- code_master は和名不要でも良いが、必要なら同様に併記可能とする

### 列構成
※ 列定義は `05_google_sheets_template.md` に完全準拠  
（know_id / product_name / course_name / rule_type / version / source_refs 等）

### 入力時の重要ルール
- **上書き禁止**
- 変更時は行コピー → version を上げる
- 旧行には effective_to を設定
- source_refs が無い行は status=approved にしない

---

## 3. code_master シート

### 目的
- 入力ゆれを防ぐ
- データ検証（ドロップダウン）に使う

### 推奨構成

#### rule_type
| value |
|------|
| RULE |
| EXCEPTION |
| PROCEDURE |
| RELIABILITY |

#### status
| value |
|------|
| draft |
| approved |
| deprecated |

#### priority（任意）
| value |
|------|
| P0 |
| P1 |
| P2 |

### code_master 初期データ（コピペ用）

#### ヘッダ（1行目）
code_type（コード種別） / code_value（値） / code_label（表示名/説明） / sort_order（並び順）

#### 初期データ（2行目以降）
- rule_type: RULE / EXCEPTION / PROCEDURE / RELIABILITY
- status: draft / approved / deprecated
- priority: P0 / P1 / P2（任意）

（Google Sheetsにはタブ区切りで貼り付ける）

---

## 4. データ検証（必須設定）

### rule_type 列
- 種類：プルダウン
- 参照先：code_master!A:A（rule_type）

### status 列
- 種類：プルダウン
- 参照先：code_master!B:B（status）

### effective_from / effective_to
- 日付形式
- 手入力OK（文字列禁止）

---

## 5. change_log シート

### 目的
- decision_log.md と対応
- シート側での変更履歴を残す

### 列例
| 日付 | know_id | 変更内容 | 理由 | 対応者 |
|----|--------|--------|------|------|
| 2025-12-23 | KU-02-001 | v2追加 | 返品除外ルール明確化 | 管理者 |

---

## 6. 最初に入れるサンプル（必須）

以下の2件を **最初の登録例** とする：

1. KU-02：縛り回数カウント（返品除外）
2. KU-05：強い解約希望（例外）

※ 実データを入れることで
- 列が足りない
- 書きにくい
- 説明不足
がすぐ見える

---

## 7. 運用ルール（最小）

- 新規追加：status=draft
- 承認後：status=approved + approved_at 記入
- 廃止：status=deprecated（削除禁止）
- 迷ったら「decision_log.md に残す」

---

## 8. MVPとの関係

- RAG / API は knowledge_units シートを **唯一の正** として参照
- Chatwork / 議事録 / スプシは **source_refs としてのみ登場**
- 「覚えている人に聞く」は運用から排除する
