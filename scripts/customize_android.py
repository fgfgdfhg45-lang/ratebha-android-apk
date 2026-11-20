"""Gives the generated Android project the Ratebha icon, splash and notification icon.

Run from the project root, after `npx cap add android`:
    pip install pillow
    python3 scripts/customize_android.py
"""
import glob
import os

from PIL import Image, ImageDraw

RES = os.path.join("android", "app", "src", "main", "res")
TEAL = (11, 110, 110, 255)
WHITE = (255, 255, 255, 255)
CHECK = [(0.29, 0.52), (0.45, 0.67), (0.72, 0.36)]


def check_layer(size, scale=1.0, k=4):
    s = size * k
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    pts = [((0.5 + (x - 0.5) * scale) * s, (0.5 + (y - 0.5) * scale) * s) for x, y in CHECK]
    w = int(s * 0.09 * scale)
    d.line(pts, fill=WHITE, width=w, joint="curve")
    for x, y in (pts[0], pts[2]):
        d.ellipse([x - w / 2, y - w / 2, x + w / 2, y + w / 2], fill=WHITE)
    return im


def down(im, size):
    return im.resize((size, size), Image.LANCZOS)


def main():
    if not os.path.isdir(RES):
        raise SystemExit("android/ folder not found. Run `npx cap add android` first.")

    k = 4
    for f in glob.glob(os.path.join(RES, "mipmap-*", "ic_launcher.png")):
        n = Image.open(f).size[0]
        s = n * k
        bg = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        ImageDraw.Draw(bg).rounded_rectangle([0, 0, s - 1, s - 1], radius=int(s * 0.22), fill=TEAL)
        bg.alpha_composite(check_layer(n))
        down(bg, n).save(f)

    for f in glob.glob(os.path.join(RES, "mipmap-*", "ic_launcher_round.png")):
        n = Image.open(f).size[0]
        s = n * k
        bg = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        ImageDraw.Draw(bg).ellipse([0, 0, s - 1, s - 1], fill=TEAL)
        bg.alpha_composite(check_layer(n, 0.9))
        down(bg, n).save(f)

    for f in glob.glob(os.path.join(RES, "mipmap-*", "ic_launcher_foreground.png")):
        n = Image.open(f).size[0]
        down(check_layer(n, 0.8), n).save(f)

    for f in glob.glob(os.path.join(RES, "drawable*", "splash.png")):
        w, h = Image.open(f).size
        im = Image.new("RGBA", (w, h), TEAL)
        m = int(min(w, h) * 0.28)
        im.alpha_composite(down(check_layer(m), m), ((w - m) // 2, (h - m) // 2))
        im.convert("RGB").save(f)

    with open(os.path.join(RES, "values", "ic_launcher_background.xml"), "w", encoding="utf8") as fh:
        fh.write(
            '<?xml version="1.0" encoding="utf-8"?>\n<resources>\n'
            '    <color name="ic_launcher_background">#0B6E6E</color>\n</resources>\n'
        )

    with open(os.path.join(RES, "drawable", "ic_stat_ratebha.xml"), "w", encoding="utf8") as fh:
        fh.write(
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<vector xmlns:android="http://schemas.android.com/apk/res/android"\n'
            '    android:width="24dp"\n    android:height="24dp"\n'
            '    android:viewportWidth="24"\n    android:viewportHeight="24">\n'
            '    <path\n        android:pathData="M5,12.5 L10,17.5 L19,7"\n'
            '        android:strokeColor="#FFFFFF"\n        android:strokeWidth="2.6"\n'
            '        android:strokeLineCap="round"\n        android:strokeLineJoin="round" />\n'
            "</vector>\n"
        )
    print("Android resources customized.")


if __name__ == "__main__":
    main()
