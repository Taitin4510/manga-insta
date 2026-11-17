"""インスタのプロフに貼る「紹介アイテムまとめページ」（docs/index.html）を作る。

drafts/ の最新7日ぶんのCSVを読み、投稿と同じ番号で並べて、もしもアフィリエイト経由の
楽天検索リンクをつける。GitHub Pages（main ブランチの /docs）で公開する想定。
"""
import csv
import glob
import html
import os
import re
import urllib.parse

CONFIG = {
    "a_id": "5907781",  # もしもアフィリエイトの紹介ID（公開リンクに含まれるもの）
    # 楽天市場の商品購入（どこでもリンク）
    "rakuten": {"p_id": "54", "pc_id": "54", "pl_id": "616"},
}
DAYS = 7


def moshimo(url, prog):
    q = urllib.parse.urlencode({"a_id": CONFIG["a_id"], **prog, "url": url})
    return f"https://af.moshimo.com/af/c/click?{q}"


def pixel(prog):
    q = urllib.parse.urlencode({"a_id": CONFIG["a_id"], **prog})
    return f"https://i.moshimo.com/af/i/impression?{q}"


def target_url(w):
    """CSVの url 列に楽天のページがあればそれを、なければ楽天の検索結果を使う"""
    u = (w.get("url") or "").strip()
    host = urllib.parse.urlparse(u).netloc.lower()
    if u.startswith("https://") and (host == "rakuten.co.jp" or host.endswith(".rakuten.co.jp")):
        return u
    return rakuten_search(w)


def rakuten_search(w):
    goods = (w.get("kind") or "").strip().lower() in ("goods", "雑貨", "item")
    kw = w.get("title", "").strip()
    if not goods:
        kw += " 漫画"
    return f"https://search.rakuten.co.jp/search/mall/{urllib.parse.quote(kw)}/"


def load_days():
    files = sorted(glob.glob("drafts/manga_*.csv"), reverse=True)[:DAYS]
    days = []
    for p in files:
        day = re.search(r"(\d{4}-\d{2}-\d{2})", p).group(1)
        with open(p, encoding="utf-8-sig", newline="") as f:
            rows = [r for r in csv.DictReader(f) if (r.get("title") or "").strip()]
        days.append((day, rows))
    return days


def card(i, w):
    e = lambda s: html.escape((s or "").strip())
    goods = (w.get("kind") or "").strip().lower() in ("goods", "雑貨", "item")
    badge = f'<span class="badge">{e(w.get("badge"))}</span>' if (w.get("badge") or "").strip() else ""
    kind = "雑貨" if goods else "漫画"
    link = moshimo(target_url(w), CONFIG["rakuten"])
    return f'''<li class="card">
  <div class="top"><span class="num">{i}</span><span class="kind">{kind}</span>{badge}</div>
  <h3>{e(w.get("title"))}</h3>
  <p class="catch">{e(w.get("catch"))}</p>
  <a class="btn" href="{html.escape(link)}" rel="nofollow sponsored noopener" referrerpolicy="no-referrer-when-downgrade" target="_blank">楽天でチェック</a>
</li>'''


def build():
    days = load_days()
    sections = []
    for n, (day, rows) in enumerate(days):
        y, m, d = day.split("-")
        title = "今日の紹介" if n == 0 else f"{int(m)}月{int(d)}日の紹介"
        cards = "\n".join(card(i, w) for i, w in enumerate(rows, 1))
        sections.append(f'<section><h2>{title}</h2><ol class="cards">{cards}</ol></section>')
    px = pixel(CONFIG["rakuten"])
    page = f'''<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>漫画と雑貨 毎日おすすめ｜紹介アイテム一覧</title>
<meta name="robots" content="noindex">
<style>
:root{{--ink:#111;--accent:#FFD43B;--ground:#5B9BD5;--red:#C81E2D}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--ground);font-family:"Hiragino Sans","Noto Sans JP",sans-serif;color:var(--ink)}}
header{{background:var(--ink);color:var(--accent);padding:20px 16px;text-align:center}}
header h1{{margin:0;font-size:22px}}
header p{{margin:6px 0 0;color:#fff;font-size:13px}}
main{{max-width:560px;margin:0 auto;padding:16px}}
.pr{{background:#fff;border:2px solid var(--ink);border-radius:10px;padding:10px 12px;font-size:12px;line-height:1.6;margin-bottom:16px}}
h2{{font-size:18px;background:var(--accent);border:3px solid var(--ink);border-radius:999px;display:inline-block;padding:4px 16px;margin:16px 0 10px}}
.cards{{list-style:none;padding:0;margin:0;display:grid;gap:12px}}
.card{{background:#fff;border:3px solid var(--ink);border-radius:16px;padding:14px;box-shadow:6px 6px 0 var(--ink)}}
.top{{display:flex;gap:8px;align-items:center;flex-wrap:wrap}}
.num{{width:32px;height:32px;border-radius:50%;background:var(--accent);border:3px solid var(--ink);display:inline-flex;align-items:center;justify-content:center;font-weight:900}}
.kind{{font-size:12px;font-weight:700;border:2px solid var(--ink);border-radius:999px;padding:2px 10px}}
.badge{{font-size:12px;font-weight:900;color:#fff;background:var(--red);border-radius:999px;padding:3px 10px}}
.card h3{{margin:10px 0 4px;font-size:18px}}
.catch{{margin:0 0 12px;font-size:14px;color:#333}}
.btn{{display:block;text-align:center;background:var(--accent);color:var(--ink);font-weight:900;border:3px solid var(--ink);border-radius:999px;padding:12px;text-decoration:none;min-height:44px}}
.btn:active{{transform:translate(2px,2px)}}
footer{{text-align:center;color:#fff;font-size:12px;padding:24px 16px}}
</style>
</head>
<body>
<header><h1>漫画と雑貨 毎日おすすめ</h1><p>インスタの投稿と同じ番号で並んでるよ</p></header>
<main>
<p class="pr">【PR】このページにはアフィリエイトリンク（広告）が含まれています。リンク先で購入されると、運営者に報酬が支払われることがあります。価格や在庫はリンク先でご確認ください。</p>
{"".join(sections) or "<p>準備中です</p>"}
</main>
<footer>@manga45102026</footer>
<img src="{html.escape(px)}" width="1" height="1" style="border:none" alt="" loading="lazy">
</body>
</html>
'''
    os.makedirs("docs", exist_ok=True)
    with open("docs/index.html", "w", encoding="utf-8") as f:
        f.write(page)
    with open("docs/.nojekyll", "w") as f:
        f.write("")
    print(f"docs/index.html を更新（{len(days)}日ぶん）")


if __name__ == "__main__":
    build()
