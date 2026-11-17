"""CSV（drafts/manga_YYYY-MM-DD.csv）から、インスタ用の紹介画像（JPEG 1080x1350）を2枚ずつ作る。

使い方: python scripts/render.py drafts/manga_2026-11-17.csv
出力先: images/2026-11-17/{番号}_1.jpg, {番号}_2.jpg
"""
import csv
import os
import re
import sys

from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1350
INK = (17, 17, 17)
WHITE = (255, 255, 255)
GRAY = (68, 68, 68)
ACCENT = (255, 212, 59)   # #FFD43B
GROUND = (91, 155, 213)   # #5B9BD5

FONT_DIR = os.environ.get("FONT_DIR", "/usr/share/fonts/opentype/noto")
FONT_FILES = {
    "black": "NotoSansCJK-Black.ttc",
    "bold": "NotoSansCJK-Bold.ttc",
    "medium": "NotoSansCJK-Medium.ttc",
}
_cache = {}


def font(weight, size):
    key = (weight, size)
    if key not in _cache:
        path = os.path.join(FONT_DIR, FONT_FILES[weight])
        if not os.path.exists(path):  # Medium/Bold が無い環境の予備
            path = os.path.join(FONT_DIR, "NotoSansCJK-Regular.ttc")
        _cache[key] = ImageFont.truetype(path, size, index=0)  # index 0 = JP
    return _cache[key]


NO_START = "、。，．・：；？！ー」』）】〕〉》ゝゞぁぃぅぇぉっゃゅょゎァィゥェォッャュョヮヵヶ…"


def text_w(f, s):
    return f.getlength(s)


def wrap(f, text, max_w):
    lines = []
    for para in str(text).split("\n"):
        line = ""
        for ch in para:
            t = line + ch
            if text_w(f, t) > max_w and line:
                if ch in NO_START:
                    lines.append(t)
                    line = ""
                else:
                    lines.append(line)
                    line = ch
            else:
                line = t
        lines.append(line)
    return lines


def rr(d, box, r, fill=None, outline=None, width=0):
    d.rounded_rectangle(box, radius=r, fill=fill, outline=outline, width=width)


def text_mid(d, x, y_mid, s, f, fill, anchor="lm"):
    d.text((x, y_mid), s, font=f, fill=fill, anchor=anchor)


def pr_box(d, right, top):
    f = font("bold", 28)
    w = text_w(f, "PR") + 40
    rr(d, (right - w, top, right, top + 52), 8, fill=WHITE, outline=INK, width=3)
    text_mid(d, right - w / 2, top + 26, "PR", f, INK, "mm")


def draw_cover(w):
    img = Image.new("RGB", (W, H), GROUND)
    d = ImageDraw.Draw(img)
    f = font("black", 34)
    label = "今日のおすすめ漫画"
    pw = text_w(f, label) + 56
    rr(d, (72, 72, 72 + pw, 136), 32, fill=INK)
    text_mid(d, 100, 104, label, f, ACCENT)
    pr_box(d, W - 72, 78)

    cx, cy, cw, ch = 72, 176, 936, 1004
    rr(d, (cx + 16, cy + 16, cx + 16 + cw, cy + 16 + ch), 32, fill=INK)
    rr(d, (cx, cy, cx + cw, cy + ch), 32, fill=WHITE, outline=INK, width=6)
    inner_x, inner_w = cx + 64, cw - 128

    size = 112
    while True:
        tf = font("black", size)
        tlines = wrap(tf, w.get("title") or "[作品タイトル]", inner_w)
        if len(tlines) <= 3 or size <= 64:
            break
        size -= 4
    tlh = size * 1.25
    cf = font("black", 46)
    clines = wrap(cf, f"「{w.get('catch', '')}」", inner_w - 72)
    catch_h = len(clines) * 64 + 56
    tags = [t for t in (w.get("tag1"), w.get("tag2"), w.get("tag3")) if t]
    total = 50 + 40 + len(tlines) * tlh + 40 + catch_h + (100 if tags else 0)
    y = cy + (ch - total) / 2

    text_mid(d, inner_x, y + 25, w.get("genre", ""), font("bold", 36), GRAY)
    y += 90
    for i, l in enumerate(tlines):
        text_mid(d, inner_x, y + tlh * i + tlh / 2, l, tf, INK)
    y += len(tlines) * tlh + 40
    d.rectangle((inner_x, y, inner_x + inner_w, y + catch_h), fill=ACCENT, outline=INK, width=5)
    for i, l in enumerate(clines):
        text_mid(d, inner_x + 36, y + 28 + 64 * i + 32, l, cf, INK)
    y += catch_h + 40
    gf = font("bold", 30)
    tx = inner_x
    for t in tags:
        lab = "#" + t.lstrip("#")
        tw = text_w(gf, lab) + 52
        if tx + tw > inner_x + inner_w:
            break
        rr(d, (tx, y, tx + tw, y + 60), 30, outline=INK, width=3)
        text_mid(d, tx + 26, y + 30, lab, gf, INK)
        tx += tw + 16

    text_mid(d, 72, 1253, "推しポイントはスワイプ", font("black", 34), INK)
    d.line((W - 140, 1253, W - 80, 1253), fill=INK, width=6)
    d.line((W - 98, 1237, W - 80, 1253, W - 98, 1269), fill=INK, width=6, joint="curve")
    return img


def draw_points(w):
    img = Image.new("RGB", (W, H), GROUND)
    d = ImageDraw.Draw(img)
    d.text((72, 120), "推しポイント", font=font("black", 72), fill=WHITE,
           stroke_width=4, stroke_fill=INK, anchor="lm")
    pr_box(d, W - 72, 94)

    px, py, pw = 72, 204, 936
    text_x = px + 48 + 72 + 28
    text_wd = pw - 96 - 100
    pf = font("bold", 40)
    pts = [wrap(pf, w.get(k, ""), text_wd) for k in ("point1", "point2", "point3")]
    ph = 80 + sum(max(72, len(l) * 60) for l in pts) + 56
    rr(d, (px + 12, py + 12, px + 12 + pw, py + 12 + ph), 28, fill=INK)
    rr(d, (px, py, px + pw, py + ph), 28, fill=WHITE, outline=INK, width=6)
    y = py + 40
    nf = font("black", 36)
    for i, lines in enumerate(pts):
        c = (px + 48 + 36, y + 36)
        d.ellipse((c[0] - 34, c[1] - 34, c[0] + 34, c[1] + 34), fill=ACCENT, outline=INK, width=4)
        text_mid(d, c[0], c[1], str(i + 1), nf, INK, "mm")
        for j, l in enumerate(lines):
            text_mid(d, text_x, y + 36 + 60 * j, l, pf, INK)
        y += max(72, len(lines) * 60) + 28

    cta_y, cta_h = 1170, 108
    rr(d, (72, cta_y, 72 + 936, cta_y + cta_h), 54, fill=ACCENT, outline=INK, width=6)
    text_mid(d, W / 2, cta_y + cta_h / 2, "続きはプロフィールのリンクから", font("black", 40), INK, "mm")

    sy = py + ph + 32
    sh = cta_y - 32 - sy
    rr(d, (72, sy, 72 + 936, sy + sh), 28, fill=WHITE, outline=INK, width=6)
    text_mid(d, 120, sy + 56, "あらすじ", font("black", 32), INK)
    room = sh - 56 - 40 - 80
    size = 34
    while True:
        sf = font("medium", size)
        lines = wrap(sf, w.get("synopsis", ""), 840)
        if len(lines) * size * 1.6 <= room or size <= 22:
            break
        size -= 2
    for i, l in enumerate(lines):
        text_mid(d, 120, sy + 110 + size * 1.6 * i, l, sf, INK)
    parts = [(lab, w.get(k, "")) for lab, k in (("作者", "author"), ("出版社", "publisher"), ("既刊", "volumes"))]
    info = "　".join(f"{lab}：{v}" for lab, v in parts if v)
    text_mid(d, 120, sy + sh - 44, info, font("bold", 26), GRAY)
    return img


SW, SH = 1080, 1920  # ストーリー・リール（9:16）


def frame_916(post_img, top_label, bottom_label):
    """1080x1350 の投稿画像を 9:16 の枠に入れる"""
    img = Image.new("RGB", (SW, SH), GROUND)
    d = ImageDraw.Draw(img)
    f = font("black", 44)
    w = text_w(f, top_label) + 72
    rr(d, ((SW - w) / 2, 120, (SW + w) / 2, 210), 45, fill=INK)
    text_mid(d, SW / 2, 165, top_label, f, ACCENT, "mm")
    s = post_img.resize((1000, 1250))
    img.paste(s, (40, 290))
    rr(d, (40, 290, 1040, 1540), 8, outline=INK, width=6)
    bf = font("black", 50)
    rr(d, (90, 1640, SW - 90, 1760), 60, fill=ACCENT, outline=INK, width=6)
    text_mid(d, SW / 2, 1700, bottom_label, bf, INK, "mm")
    return img


def make_reel(frames, out_path, tmp_dir, sec=4, fade=0.6, seed="bgm"):
    """静止画を順番にクロスフェードでつなぎ、オリジナルBGMをつけたリール動画（H.264 / AAC）を作る"""
    import subprocess
    from music import make_bgm
    paths = []
    for n, fr in enumerate(frames):
        p = os.path.join(tmp_dir, f"_reel_{n}.jpg")
        fr.save(p, "JPEG", quality=92)
        paths.append(p)
    cmd = ["ffmpeg", "-y", "-loglevel", "error"]
    for p in paths:
        cmd += ["-loop", "1", "-t", str(sec), "-i", p]
    total = sec * len(paths) - fade * (len(paths) - 1)
    bgm = os.path.join(tmp_dir, "_bgm.wav")
    make_bgm(bgm, total, seed)
    cmd += ["-i", bgm]
    chain, last = [], "[0:v]"
    for k in range(1, len(paths)):
        out = f"[v{k}]"
        chain.append(f"{last}[{k}:v]xfade=transition=fade:duration={fade}:offset={sec * k - fade * k:.2f}{out}")
        last = out
    chain.append(f"{last}format=yuv420p,fps=30[vout]")
    cmd += ["-filter_complex", ";".join(chain), "-map", "[vout]", "-map", f"{len(paths)}:a",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-profile:v", "high",
            "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", "-shortest", out_path]
    subprocess.run(cmd, check=True)
    for p in paths + [bgm]:
        os.remove(p)


def read_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return [r for r in csv.DictReader(f) if (r.get("title") or "").strip()]


def date_of(path):
    m = re.search(r"(\d{4}-\d{2}-\d{2})", os.path.basename(path))
    if not m:
        raise SystemExit(f"ファイル名に日付がありません: {path}")
    return m.group(1)


def main(path, force=False):
    day = date_of(path)
    out = os.path.join("images", day)
    if os.path.exists(os.path.join(out, "1_reel.mp4")) and not force:
        print(f"{day}: 作成ずみなのでスキップ")
        return
    os.makedirs(out, exist_ok=True)
    works = read_csv(path)
    for i, w in enumerate(works, 1):
        w = {k: (v or "").strip() for k, v in w.items()}
        cover, points = draw_cover(w), draw_points(w)
        cover.save(os.path.join(out, f"{i}_1.jpg"), "JPEG", quality=92)
        points.save(os.path.join(out, f"{i}_2.jpg"), "JPEG", quality=92)
        frame_916(cover, "NEW POST", "続きはプロフのリンクから").save(
            os.path.join(out, f"{i}_story.jpg"), "JPEG", quality=92)
        make_reel([frame_916(cover, "今日のおすすめ漫画", "推しポイントは次へ"),
                   frame_916(points, "今日のおすすめ漫画", "続きはプロフのリンクから")],
                  os.path.join(out, f"{i}_reel.mp4"), out, seed=f"{day}-{i}")
    print(f"{day}: {len(works)}作品ぶんの画像を作成")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--force"]
    for p in args:
        main(p, force="--force" in sys.argv)
