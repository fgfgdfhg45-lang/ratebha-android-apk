"""Gives the generated Android project the Ratebha icon, splash, permissions and build number.

Run from the project root, after `npx cap add android`:
    pip install pillow
    python3 scripts/customize_android.py
"""
import glob
import math
import os
import struct
import wave

from PIL import Image, ImageDraw

RES = os.path.join("android", "app", "src", "main", "res")
BLACK = (17, 17, 17, 255)
WHITE = (255, 255, 255, 255)

# Three bars, longest first, lined up on the right: an ordered list.
# (x_right, width, y_top, height) in fractions of the icon size.
BARS = [
    (0.70, 0.40, 0.3275, 0.075),
    (0.70, 0.30, 0.4625, 0.075),
    (0.70, 0.20, 0.5975, 0.075),
]


def bars_layer(size, scale=1.0, k=4):
    s = size * k
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for xr, w, y, h in BARS:
        x1 = 0.5 + (xr - 0.5) * scale
        x0 = x1 - w * scale
        y0 = 0.5 + (y - 0.5) * scale
        y1 = y0 + h * scale
        d.rounded_rectangle([x0 * s, y0 * s, x1 * s, y1 * s], radius=int(s * 0.012 * scale), fill=WHITE)
    return im


def down(im, size):
    return im.resize((size, size), Image.LANCZOS)


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf8") as fh:
        fh.write(text)


def icons():
    k = 4
    for f in glob.glob(os.path.join(RES, "mipmap-*", "ic_launcher.png")):
        n = Image.open(f).size[0]
        s = n * k
        bg = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        ImageDraw.Draw(bg).rounded_rectangle([0, 0, s - 1, s - 1], radius=int(s * 0.18), fill=BLACK)
        bg.alpha_composite(bars_layer(n))
        down(bg, n).save(f)

    for f in glob.glob(os.path.join(RES, "mipmap-*", "ic_launcher_round.png")):
        n = Image.open(f).size[0]
        s = n * k
        bg = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        ImageDraw.Draw(bg).ellipse([0, 0, s - 1, s - 1], fill=BLACK)
        bg.alpha_composite(bars_layer(n, 0.92))
        down(bg, n).save(f)

    for f in glob.glob(os.path.join(RES, "mipmap-*", "ic_launcher_foreground.png")):
        n = Image.open(f).size[0]
        down(bars_layer(n, 1.0), n).save(f)

    for f in glob.glob(os.path.join(RES, "drawable*", "splash.png")):
        w, h = Image.open(f).size
        im = Image.new("RGBA", (w, h), BLACK)
        m = int(min(w, h) * 0.34)
        im.alpha_composite(down(bars_layer(m), m), ((w - m) // 2, (h - m) // 2))
        im.convert("RGB").save(f)

    write(
        os.path.join(RES, "values", "ic_launcher_background.xml"),
        '<?xml version="1.0" encoding="utf-8"?>\n<resources>\n'
        '    <color name="ic_launcher_background">#111111</color>\n</resources>\n',
    )

    # Small status-bar icon: the same three bars, white only.
    write(
        os.path.join(RES, "drawable", "ic_stat_ratebha.xml"),
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<vector xmlns:android="http://schemas.android.com/apk/res/android"\n'
        '    android:width="24dp"\n    android:height="24dp"\n'
        '    android:viewportWidth="24"\n    android:viewportHeight="24">\n'
        '    <path\n        android:fillColor="#FFFFFF"\n'
        '        android:pathData="M6,6h12v2H6z M9,11h9v2H9z M12,16h6v2h-6z" />\n'
        "</vector>\n",
    )


def chime(path):
    """A soft three-note rising chime (E5, A5, C#6) with a bell-like tail, about 2.4 seconds."""
    rate = 44100
    length = 2.4
    notes = [(0.00, 659.25, 1.00), (0.22, 880.00, 0.90), (0.44, 1108.73, 0.80)]
    partials = [(1.0, 1.00, 2.6), (2.0, 0.28, 4.2), (3.0, 0.10, 6.0), (4.2, 0.05, 9.0)]
    n = int(rate * length)
    samples = [0.0] * n
    for start, freq, amp in notes:
        i0 = int(start * rate)
        for ratio, a, decay in partials:
            for detune in (0.0, 1.3):
                f = freq * ratio + detune
                gain = amp * a * (0.5 if detune else 0.5)
                for i in range(i0, n):
                    t = (i - i0) / rate
                    attack = min(1.0, t / 0.006)
                    samples[i] += gain * attack * math.exp(-decay * t) * math.sin(2 * math.pi * f * t)
    peak = max(abs(v) for v in samples) or 1.0
    scale = 0.7 / peak
    fade = int(rate * 0.15)
    frames = bytearray()
    for i, v in enumerate(samples):
        if i > n - fade:
            v *= (n - i) / fade
        frames += struct.pack("<h", int(max(-1.0, min(1.0, v * scale)) * 32767))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(bytes(frames))


def patch_manifest_and_version():
    """Exact alarms (no prompt on sideloaded apps) and a build number that grows with every build."""
    mf = os.path.join("android", "app", "src", "main", "AndroidManifest.xml")
    with open(mf, encoding="utf8") as fh:
        text = fh.read()
    perms = [
        "android.permission.USE_EXACT_ALARM",
        "android.permission.SCHEDULE_EXACT_ALARM",
        "android.permission.RECEIVE_BOOT_COMPLETED",
        "android.permission.POST_NOTIFICATIONS",
    ]
    add = "".join(
        '    <uses-permission android:name="%s" />\n' % p for p in perms if p not in text
    )
    if add:
        marker = "<!-- Permissions -->"
        if marker in text:
            text = text.replace(marker, marker + "\n" + add, 1)
        else:
            text = text.replace("</manifest>", add + "</manifest>", 1)
        with open(mf, "w", encoding="utf8") as fh:
            fh.write(text)

    cfg = "capacitor.config.ts"
    if os.path.exists(cfg):
        with open(cfg, encoding="utf8") as fh:
            ct = fh.read()
        for old in ("#0B6E6E", "#4A7C74"):
            ct = ct.replace(old, "#111111")
        with open(cfg, "w", encoding="utf8") as fh:
            fh.write(ct)

    gradle = os.path.join("android", "app", "build.gradle")
    with open(gradle, encoding="utf8") as fh:
        g = fh.read()
    g = g.replace(
        "versionCode 1",
        "versionCode Integer.parseInt(System.getenv('GITHUB_RUN_NUMBER') ?: '1')",
        1,
    )
    with open(gradle, "w", encoding="utf8") as fh:
        fh.write(g)


def main():
    if not os.path.isdir(RES):
        raise SystemExit("android/ folder not found. Run `npx cap add android` first.")
    icons()
    chime(os.path.join(RES, "raw", "ratebha_chime.wav"))
    patch_manifest_and_version()
    print("Android project customized.")


if __name__ == "__main__":
    main()
