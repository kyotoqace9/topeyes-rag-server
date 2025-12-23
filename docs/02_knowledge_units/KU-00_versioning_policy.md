# KU-00：ルール版管理ポリシー（v0.1 / WIP）

## 背景（現状）
- “特定時期からルールが変わったコース”の判定は、
  覚えている人に確認 → Chatwork/議事録検索 → 根拠を掘り起こし展開、という運用になっている。
- その結果、ルールの探索コストが高く、属人化しており、知識が蓄積されにくい。

## 目的
- ルール変更（改定）が起きても、誰でも同じ結論に到達できるようにする。
- 「いつから」「どのルールが」「なぜ適用されるか」を追跡可能にする。
- 根拠（Chatwork/議事録/スプシ）を Knowledge Unit に紐付けて残す。

## 方針（結論）
- すべてのルール（Knowledge Unit）に「適用範囲（期間 or version）」と「根拠」を必須項目として持たせる。
- ルールが変わった場合は“上書き”ではなく、“新しい版（version）を追加”する。

## 必須メタデータ（Knowledge Unit 共通）
各 Knowledge Unit は最低限、以下を持つ：

- know_id：一意ID
- client_company_id：クライアント識別
- product_name：商材名（例：漲天）
- course_name：コース名（例：7回お約束コースLN）
- rule_type：RULE / EXCEPTION / PROCEDURE / RELIABILITY など
- version：v1, v2 ...（改定のたびに増やす）
- effective_from：適用開始日（YYYY-MM-DD）
- effective_to：適用終了日（YYYY-MM-DD or 空欄）
- source_refs：根拠（複数可）
  - spreadsheet：スプレッドシート名 + シート名 + 行/セル
  - minutes：議事録（開催日 + 該当箇所）
  - chatwork：Chatworkルーム + 日付 + 検索語 or メッセージURL
- summary：要点（検索でヒットさせる短文）
- body：詳細ルール本文
- tags：検索用タグ（例：解約, 縛り, アップセル, 例外, 解約金）

## 版（version）運用ルール
- ルール改定が発生したら：
  1) 旧版（v1）の effective_to に終了日を入れる
  2) 新版（v2）を作り effective_from を開始日にする
  3) 両方に根拠（source_refs）を入れる
  4) decision_log に「いつ・何を・なぜ変えたか」を記録する

- “覚えている人の知識”は、必ず source_refs に落とし込む（口頭だけで終わらせない）

## コース名変更（旧称・別名）ポリシー
- 表記揺れ/旧称は alias として扱い、検索で拾えるように tags/summary に残す。
  例：7回お約束コースLN（旧称：7回受け取りお約束コース）

## MVPでの適用（最小実装）
- version/effective_from/effective_to/source_refs を持たないナレッジは「暫定（要根拠）」として扱い、
  返答時に警告（例：「根拠未添付のためSV確認推奨」）を返す。
- まずは “改定があるコース” から優先して version を付ける。

## 期待効果
- ルール探索が「人検索」から「ナレッジ検索」に置換される
- 後任者が “いつのルールか” を読み解ける
- 改定の履歴が追跡可能になり、事故の再発防止につながる
