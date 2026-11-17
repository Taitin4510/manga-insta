"""リール用のBGMをその場で作曲する（オリジナル曲なので著作権の心配なし）。

コード進行・キー・テンポ・音色を乱数で選ぶので、毎回ちょっとずつ違う曲になる。
使い方: make_bgm("out.wav", seconds=7.4, seed="2026-11-17-1")
"""
import math
import random
import struct
import wave

SR = 44100

# よく使われる明るめ/エモめの進行（ディグリー: 0=I, 1=ii, ... メジャースケール上）
PROGRESSIONS = [
    [0, 4, 5, 3],   # I - V - vi - IV
    [5, 3, 0, 4],   # vi - IV - I - V
    [3, 4, 2, 5],   # IV - V - iii - vi（王道進行）
    [0, 5, 3, 4],   # I - vi - IV - V
    [3, 0, 4, 5],   # IV - I - V - vi
]
MAJOR = [0, 2, 4, 5, 7, 9, 11]


def midi_hz(n):
    return 440.0 * 2 ** ((n - 69) / 12)


def chord_notes(root_midi, degree):
    """スケール上の3和音（ルート・3度・5度）"""
    out = []
    for step in (0, 2, 4):
        d = degree + step
        out.append(root_midi + MAJOR[d % 7] + 12 * (d // 7))
    return out


def osc(kind, phase):
    if kind == "sine":
        return math.sin(phase)
    if kind == "tri":
        x = (phase / (2 * math.pi)) % 1.0
        return 4 * abs(x - 0.5) - 1
    # やわらかい矩形（チップチューン風）
    return math.tanh(3 * math.sin(phase)) * 0.6


def make_bgm(path, seconds, seed):
    rnd = random.Random(str(seed))
    key = rnd.choice([0, 2, 3, 5, 7, 9])          # C, D, Eb, F, G, A
    root = 60 + key - 12                          # 低めのルート
    bpm = rnd.choice([86, 92, 100, 110, 120])
    prog = rnd.choice(PROGRESSIONS)
    lead = rnd.choice(["tri", "square", "sine"])
    pattern = rnd.choice([[0, 1, 2, 1], [0, 2, 1, 2], [2, 1, 0, 1], [0, 1, 2, 3]])
    with_drums = rnd.random() < 0.8

    n = int(SR * seconds)
    beat = 60.0 / bpm
    bar = beat * 4
    eighth = beat / 2
    left = [0.0] * n
    right = [0.0] * n

    def add(start, dur, freq, amp, kind, pan=0.0, attack=0.01, release=0.15):
        s0 = int(start * SR)
        s1 = min(n, int((start + dur + release) * SR))
        ph = 0.0
        step = 2 * math.pi * freq / SR
        for s in range(max(0, s0), s1):
            t = (s - s0) / SR
            if t < attack:
                env = t / attack
            elif t < dur:
                env = 1.0 - 0.3 * (t - attack) / max(dur - attack, 1e-6)
            else:
                env = 0.7 * max(0.0, 1 - (t - dur) / release)
            v = osc(kind, ph) * env * amp
            ph += step
            left[s] += v * (1 - pan) * 0.5
            right[s] += v * (1 + pan) * 0.5

    t = 0.0
    k = 0
    while t < seconds:
        notes = chord_notes(root, prog[k % len(prog)])
        # パッド（コード）
        for j, m in enumerate(notes):
            add(t, bar * 0.95, midi_hz(m), 0.10, "sine", pan=(j - 1) * 0.4, attack=0.15, release=0.4)
        # ベース
        add(t, beat * 1.8, midi_hz(notes[0] - 12), 0.22, "sine", attack=0.02)
        add(t + beat * 2, beat * 1.8, midi_hz(notes[0] - 12), 0.20, "sine", attack=0.02)
        # アルペジオ（メロディ役）
        arp = notes + [notes[0] + 12]
        for e in range(8):
            m = arp[pattern[e % 4] % len(arp)] + 12
            add(t + e * eighth, eighth * 0.7, midi_hz(m), 0.09, lead, pan=0.3 if e % 2 else -0.3, release=0.08)
        # ドラム（キック＋ハイハットっぽいノイズ）
        if with_drums:
            for b in range(4):
                s0 = int((t + b * beat) * SR)
                for s in range(s0, min(n, s0 + int(0.18 * SR))):
                    tt = (s - s0) / SR
                    f = 110 * math.exp(-tt * 25) + 45
                    v = math.sin(2 * math.pi * f * tt) * math.exp(-tt * 18) * 0.35
                    left[s] += v
                    right[s] += v
                for h in (0.5,):
                    s0 = int((t + (b + h) * beat) * SR)
                    for s in range(s0, min(n, s0 + int(0.04 * SR))):
                        tt = (s - s0) / SR
                        v = (rnd.random() * 2 - 1) * math.exp(-tt * 90) * 0.06
                        left[s] += v
                        right[s] -= v * 0.5
        t += bar
        k += 1

    # フェードイン・アウトと音量調整
    fade_in, fade_out = int(0.3 * SR), int(0.8 * SR)
    peak = max(1e-6, max(max(abs(x) for x in left), max(abs(x) for x in right)))
    gain = 0.85 / peak
    frames = bytearray()
    for s in range(n):
        g = gain
        if s < fade_in:
            g *= s / fade_in
        if s > n - fade_out:
            g *= max(0.0, (n - s) / fade_out)
        frames += struct.pack("<hh", int(max(-1, min(1, left[s] * g)) * 32767),
                              int(max(-1, min(1, right[s] * g)) * 32767))
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(bytes(frames))
    return {"key": key, "bpm": bpm, "progression": prog, "lead": lead}


if __name__ == "__main__":
    import sys
    print(make_bgm(sys.argv[1] if len(sys.argv) > 1 else "bgm.wav", 7.4, sys.argv[2] if len(sys.argv) > 2 else "test"))
