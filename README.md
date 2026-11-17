# manga-insta

話題の漫画を、文字だけの紹介画像（2枚スワイプ）で毎日インスタに自動投稿するしくみ。漫画のページ画像は使わない。

## 流れ

1. 毎朝 6:12（日本時間）、Claude が `drafts/manga_YYYY-MM-DD.csv` に5作品ぶんの下書きを置く
2. `画像をつくる` ワークフローが `images/YYYY-MM-DD/` に JPEG を作る
3. `インスタに投稿` ワークフローが 8:07 / 12:07 / 18:07 / 20:07 / 22:07 に1件ずつ投稿する
   投稿ずみの番号は `posted/YYYY-MM-DD.json` に記録される

## 最初の設定

| Secrets の名前 | 中身 |
| --- | --- |
| `IG_ACCESS_TOKEN` | Instagram API with Instagram Login の長期アクセストークン |
| `GH_PAT` | このリポジトリの Secrets を書きかえられる fine-grained トークン（トークン自動更新用） |

Settings → Secrets and variables → Actions → New repository secret で登録する。
トークンはチャットやファイルには絶対に書かない。

## 手動で動かす

Actions タブ → ワークフローを選ぶ → Run workflow。

## CSV の列

`title,genre,catch,tag1,tag2,tag3,point1,point2,point3,synopsis,author,publisher,volumes,caption`

## 注意

- 投稿には #PR がつく
- 成人向け作品は扱わない
- 画像は公開URL（raw.githubusercontent.com）からインスタが取りにくるので、リポジトリは Public のまま
