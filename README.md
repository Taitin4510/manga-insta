# manga-insta

話題の漫画5作品と雑貨5商品を、文字だけの紹介画像（2枚スワイプ）・ストーリー・リール（オリジナルBGMつき）で毎日インスタに自動投稿するしくみ。漫画のページ画像や商品写真は使わない。

## 流れ

1. 毎朝 6:12（日本時間）、Claude が `drafts/manga_YYYY-MM-DD.csv` に10件（本と雑貨が交互）の下書きを置く
2. `画像をつくる` ワークフローが `images/YYYY-MM-DD/` に投稿画像・ストーリー画像・リール動画を作る
3. `インスタに投稿` ワークフローが 7:07〜22:07 の10回、1件ずつ（投稿＋ストーリー＋リール）投稿する
   投稿ずみの番号は `posted/YYYY-MM-DD.json` に記録される

## 最初の設定

| Secrets の名前 | 中身 |
| --- | --- |
| `IG_ACCESS_TOKEN` | Meta アプリの統合ログインで作ったシステムユーザーアクセストークン（無期限） |
| `IG_USER_ID` | 投稿先インスタアカウントのID（ビジネス設定 → Instagramアカウント で確認） |

Settings → Secrets and variables → Actions → New repository secret で登録する。
トークンはチャットやファイルには絶対に書かない。

## 手動で動かす

Actions タブ → ワークフローを選ぶ → Run workflow。

## CSV の列

`kind,title,genre,catch,tag1,tag2,tag3,point1,point2,point3,synopsis,author,publisher,volumes,caption,badge`

- `kind`: `manga`（漫画）または `goods`（雑貨）
- `badge`: 表紙の赤いバッジ（10文字まで）。「1巻無料」「アニメ放送中」など確認できた事実だけ。空欄なら出ない
- 雑貨のとき: `author`=ブランド、`publisher`=ショップ、`volumes`=価格の目安、`synopsis`=商品の説明

## 注意

- 投稿には #PR がつく
- 成人向け作品は扱わない
- 画像は公開URL（raw.githubusercontent.com）からインスタが取りにくるので、リポジトリは Public のまま
