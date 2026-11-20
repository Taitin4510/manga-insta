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

_TOKEN = os.environ.get("IG_ACCESS_TOKEN", "")
# IGAA… で始まるのはインスタ用トークン（graph.instagram.com）、それ以外は Facebook 系（graph.facebook.com）
_DEFAULT_HOST = "https://graph.instagram.com" if _TOKEN.startswith("IG") else "https://graph.facebook.com"
API = os.environ.get("GRAPH_HOST", _DEFAULT_HOST) + "/" + os.environ.get("GRAPH_VERSION", "v27.0")
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


def caption_of(w, n=None):
    tags = " ".join("#" + t.strip().lstrip("#") for t in (w.get("tag1"), w.get("tag2"), w.get("tag3")) if t and t.strip())
    goods = (w.get("kind") or "").strip().lower() in ("goods", "雑貨", "item")
    head = w.get("caption") or f"{w.get('title', '')}\n{w.get('catch', '')}"
    lines = [
        head,
        "",
        f"{'🛍️' if goods else '📚'}『{w.get('title', '')}』",
        f"「{w.get('catch', '')}」",
        *([f"🔥{w.get('badge').strip()}"] if (w.get("badge") or "").strip() else []),
        "",
        *[f"✔️{w.get(k).strip()}" for k in ("point1", "point2", "point3") if (w.get(k) or "").strip()],
        "",
        (f"気になったらプロフのリンクの【{n}番】をチェックしてね" if n else "気になったらプロフのリンクからチェックしてね") + ("🛍️" if goods else "📚"),
        "🔖あとで見返せるように保存しておくのがおすすめ",
        ("💬使ってみたい人はコメントで教えて！" if goods else "💬読んだことある人はコメントで教えて！"),
        "",
        (f"#PR #おすすめ雑貨 #便利グッズ {tags}" if goods else f"#PR #漫画紹介 #おすすめ漫画 {tags}").strip(),
    ]
    return "\n".join(lines)


KINDS = ("feed", "story", "reel")


def load_log(path):
    if not os.path.exists(path):
        return {k: [] for k in KINDS}
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):  # 旧形式（フィード投稿だけの記録）
        data = {"feed": data}
    return {k: list(data.get(k, [])) for k in KINDS}


def save_log(path, log):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({k: sorted(v) for k, v in log.items()}, f)


def check_url(u):
    try:
        urllib.request.urlopen(urllib.request.Request(u, method="HEAD"), timeout=30)
        return True
    except urllib.error.URLError:
        return False


def post_feed(uid, urls, caption):
    children = []
    for u in urls:
        c = call("POST", f"{uid}/media", image_url=u, is_carousel_item="true")["id"]
        wait_ready(c)
        children.append(c)
    carousel = call("POST", f"{uid}/media", media_type="CAROUSEL",
                    children=",".join(children), caption=caption)["id"]
    wait_ready(carousel)
    return call("POST", f"{uid}/media_publish", creation_id=carousel).get("id")


def post_story(uid, url):
    c = call("POST", f"{uid}/media", media_type="STORIES", image_url=url)["id"]
    wait_ready(c)
    return call("POST", f"{uid}/media_publish", creation_id=c).get("id")


def post_reel(uid, video_path, caption):
    """動画ファイルを直接アップロード（resumable upload）してリールを投稿する"""
    res = call("POST", f"{uid}/media", media_type="REELS", upload_type="resumable",
               caption=caption, share_to_feed="false")
    cid = res["id"]
    upload_uri = res.get("uri") or f"https://rupload.facebook.com/ig-api-upload/{API.rsplit('/', 1)[1]}/{cid}"
    with open(video_path, "rb") as f:
        body = f.read()
    req = urllib.request.Request(upload_uri, data=body, method="POST", headers={
        "Authorization": f"OAuth {os.environ['IG_ACCESS_TOKEN']}",
        "offset": "0",
        "file_size": str(len(body)),
    })
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            r.read()
    except urllib.error.HTTPError as e:
        raise SystemExit(f"動画アップロードに失敗 {e.code}: {e.read().decode(errors='replace')}")
    for _ in range(60):  # 動画は処理に時間がかかる（最大5分待つ）
        st = call("GET", cid, fields="status_code").get("status_code")
        if st == "FINISHED":
            break
        if st in ("ERROR", "EXPIRED"):
            raise SystemExit(f"リールの処理に失敗: {st}")
        time.sleep(5)
    else:
        raise SystemExit("リールの処理がタイムアウト")
    return call("POST", f"{uid}/media_publish", creation_id=cid).get("id")


def main():
    day = os.environ.get("POST_DATE") or dt.datetime.now(JST).strftime("%Y-%m-%d")
    csv_path = f"drafts/manga_{day}.csv"
    if not os.path.exists(csv_path):
        print(f"{csv_path} がないので今日はスキップ")
        return
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        works = [r for r in csv.DictReader(f) if (r.get("title") or "").strip()]

    log_path = f"posted/{day}.json"
    log = load_log(log_path)
    only = [k.strip() for k in os.environ.get("ONLY_KINDS", "").split(",") if k.strip() in KINDS]
    kinds = only or list(KINDS)
    max_items = int(os.environ.get("MAX_ITEMS", "5"))   # 1日に紹介する件数（アカウントを慣らす間は少なめ）
    max_reels = int(os.environ.get("MAX_REELS", "2"))   # 1日のリール本数
    if len(log["reel"]) >= max_reels and "reel" in kinds and not only:
        kinds.remove("reel")
    todo = [i for i in range(1, min(len(works), max_items) + 1) if any(i not in log[k] for k in kinds)]
    if not todo:
        print("今日のぶんは全部投稿ずみ")
        return
    i = todo[0]
    w = {k: (v or "").strip() for k, v in works[i - 1].items()}

    uid = os.environ.get("IG_USER_ID", "").strip()
    if not uid and "graph.instagram.com" in API:
        uid = str(call("GET", "me", fields="user_id")["user_id"])
    if not uid:
        raise SystemExit("IG_USER_ID が設定されていません（GitHub Secrets を確認してね）")

    repo = os.environ["GITHUB_REPOSITORY"]
    base = f"https://raw.githubusercontent.com/{repo}/main/images/{day}"
    caption = caption_of(w, i)
    errors = []

    def attempt(kind, fn):
        try:
            mid = fn()
            log[kind].append(i)
            save_log(log_path, log)
            print(f"{kind} を投稿しました: {i}. {w.get('title')} (media id {mid})")
        except SystemExit as e:
            errors.append(f"{kind}: {e}")
            print(f"{kind} の投稿に失敗: {e}")

    if "feed" in kinds and i not in log["feed"]:
        urls = [f"{base}/{i}_1.jpg", f"{base}/{i}_2.jpg"]
        if not all(check_url(u) for u in urls):
            raise SystemExit(f"画像がまだ公開されていません: {urls}")
        attempt("feed", lambda: post_feed(uid, urls, caption))
    if "story" in kinds and i not in log["story"]:
        u = f"{base}/{i}_story.jpg"
        if check_url(u):
            attempt("story", lambda: post_story(uid, u))
        else:
            errors.append(f"story: 画像がありません {u}")
    if "reel" in kinds and i not in log["reel"]:
        v = f"images/{day}/{i}_reel.mp4"
        if os.path.exists(v):
            attempt("reel", lambda: post_reel(uid, v, caption))
        else:
            errors.append(f"reel: 動画がありません {v}")
    if errors:
        raise SystemExit("一部の投稿に失敗しました:\n" + "\n".join(errors))


if __name__ == "__main__":
    if not os.environ.get("IG_ACCESS_TOKEN"):
        sys.exit("IG_ACCESS_TOKEN が設定されていません（GitHub Secrets を確認してね）")
    main()
