"""今日（日本時間）のCSVから、まだ投稿していない作品を1件だけインスタに投稿する。

GitHub Actions から1日5回呼ばれる想定。投稿済みの番号は posted/YYYY-MM-DD.json に記録する。
必要な環境変数:
  IG_ACCESS_TOKEN    システムユーザーのアクセストークン（統合ログイン / 無期限。GitHub Secrets）
  IG_USER_ID         投稿先インスタアカウントのID（GitHub Secrets）
  GITHUB_REPOSITORY  例: Taitin4510/manga-insta（Actions が自動で入れる）
"""
import csv
import datetime as dt
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

API = os.environ.get("GRAPH_HOST", "https://graph.facebook.com") + "/" + os.environ.get("GRAPH_VERSION", "v27.0")
JST = dt.timezone(dt.timedelta(hours=9))


def call(method, path, **params):
    params["access_token"] = os.environ["IG_ACCESS_TOKEN"]
    data = urllib.parse.urlencode(params).encode()
    url = f"{API}/{path}"
    if method == "GET":
        req = urllib.request.Request(url + "?" + data.decode())
    else:
        req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        raise SystemExit(f"API エラー {e.code} ({path}): {body}")


def wait_ready(container_id):
    for _ in range(30):
        st = call("GET", container_id, fields="status_code").get("status_code")
        if st == "FINISHED":
            return
        if st in ("ERROR", "EXPIRED"):
            raise SystemExit(f"コンテナの処理に失敗: {container_id} {st}")
        time.sleep(5)
    raise SystemExit(f"コンテナの処理がタイムアウト: {container_id}")


def caption_of(w):
    tags = " ".join("#" + t.strip().lstrip("#") for t in (w.get("tag1"), w.get("tag2"), w.get("tag3")) if t and t.strip())
    head = w.get("caption") or f"{w.get('title', '')}\n{w.get('catch', '')}"
    lines = [
        head,
        "",
        f"📚『{w.get('title', '')}』",
        f"「{w.get('catch', '')}」",
        "",
        "続きはプロフィールのリンクから📚",
        "",
        f"#PR #漫画紹介 #おすすめ漫画 {tags}".strip(),
    ]
    return "\n".join(lines)


def main():
    day = os.environ.get("POST_DATE") or dt.datetime.now(JST).strftime("%Y-%m-%d")
    csv_path = f"drafts/manga_{day}.csv"
    if not os.path.exists(csv_path):
        print(f"{csv_path} がないので今日はスキップ")
        return
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        works = [r for r in csv.DictReader(f) if (r.get("title") or "").strip()]

    log_path = f"posted/{day}.json"
    posted = []
    if os.path.exists(log_path):
        with open(log_path, encoding="utf-8") as f:
            posted = json.load(f)
    todo = [i for i in range(1, len(works) + 1) if i not in posted]
    if not todo:
        print("今日のぶんは全部投稿ずみ")
        return
    i = todo[0]
    w = {k: (v or "").strip() for k, v in works[i - 1].items()}

    repo = os.environ["GITHUB_REPOSITORY"]
    base = f"https://raw.githubusercontent.com/{repo}/main/images/{day}"
    urls = [f"{base}/{i}_1.jpg", f"{base}/{i}_2.jpg"]
    for u in urls:
        try:
            urllib.request.urlopen(urllib.request.Request(u, method="HEAD"), timeout=30)
        except urllib.error.URLError:
            raise SystemExit(f"画像がまだ公開されていません: {u}")

    uid = os.environ.get("IG_USER_ID", "").strip()
    if not uid:
        raise SystemExit("IG_USER_ID が設定されていません（GitHub Secrets を確認してね）")
    children = []
    for u in urls:
        c = call("POST", f"{uid}/media", image_url=u, is_carousel_item="true")["id"]
        wait_ready(c)
        children.append(c)
    carousel = call("POST", f"{uid}/media", media_type="CAROUSEL",
                    children=",".join(children), caption=caption_of(w))["id"]
    wait_ready(carousel)
    media = call("POST", f"{uid}/media_publish", creation_id=carousel)
    print(f"投稿しました: {i}. {w.get('title')} (media id {media.get('id')})")

    os.makedirs("posted", exist_ok=True)
    posted.append(i)
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(sorted(posted), f)


if __name__ == "__main__":
    if not os.environ.get("IG_ACCESS_TOKEN"):
        sys.exit("IG_ACCESS_TOKEN が設定されていません（GitHub Secrets を確認してね）")
    main()
