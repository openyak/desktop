"""Generate macOS-native tray template + squircle app icons from the YAK logo.

Outputs (next to this file):
  tray-template.png        — pure-white YAK silhouette, transparent, ~22pt menu bar
  tray-template@2x.png     — Retina version
  macos-icon-1024.png      — squircle app icon (used to rebuild icon.icns)
"""

from pathlib import Path

from PIL import Image

ICON_DIR = Path(__file__).resolve().parent
SOURCE = ICON_DIR / "OpenYak logo" / "Yak@3x.png"


def trim_to_content(img: Image.Image) -> Image.Image:
    bbox = img.split()[-1].getbbox()
    return img.crop(bbox) if bbox else img


def extract_letter_mask(src: Image.Image, black_threshold: int = 110) -> Image.Image:
    """Binary alpha mask of the YAK *letter interiors* — not outline or shadow.

    The source logo stacks: outer drop shadow (black) → letter outline (black) →
    letter fill (yellow / white / blue). Keeping only pixels whose max channel
    clears `black_threshold` isolates the three letter fills so Y | A | K read as
    distinct glyphs, with the natural gaps where the outlines used to be. The
    mask is hard-binary (0 or 255) to avoid gray fringe when blended on colored
    menu bars — we rely on supersampling + downscale for edge smoothness.
    """
    rgba = src.convert("RGBA")
    w, h = rgba.size
    mask = Image.new("L", (w, h), 0)
    src_px = rgba.load()
    mask_px = mask.load()
    for y in range(h):
        for x in range(w):
            r, g, b, a = src_px[x, y]
            if a < 128:
                continue
            if max(r, g, b) <= black_threshold:
                continue
            mask_px[x, y] = 255
    return mask


def white_template(src: Image.Image, target_height: int, pad: int = 1) -> Image.Image:
    """Pure-white YAK silhouette, rectangular, tight-cropped to letter bbox.

    `target_height` is the intended pixel height at 1x or 2x (e.g. 44 for @2x on
    a 22pt menu bar). The output keeps the letters' natural wide aspect so they
    fill the menu bar vertically — the square-canvas padding from the previous
    version was shrinking them visually. Alpha is strictly {0, 255}; RGB is
    always pure white.
    """
    mask_full = extract_letter_mask(src)
    bbox = mask_full.getbbox()
    cropped = mask_full.crop(bbox) if bbox else mask_full
    cw, ch = cropped.size
    scale = target_height / ch
    new_w, new_h = max(1, int(round(cw * scale))), target_height
    resized = cropped.resize((new_w, new_h), Image.LANCZOS)
    # Re-binarize after resample to kill any gray edge pixels LANCZOS may have
    # introduced — guarantees pure white, never colored or semi-transparent.
    binary = resized.point(lambda v: 255 if v >= 128 else 0, mode="L")
    # Pre-fill RGB as pure white everywhere, then stamp the binary mask as alpha.
    # Transparent pixels carry RGB=(255,255,255,0) so the file is literally
    # "pure white and nothing else" — no black RGB lurking under alpha=0.
    canvas = Image.new("RGBA", (new_w + pad * 2, new_h + pad * 2), (255, 255, 255, 0))
    alpha = Image.new("L", canvas.size, 0)
    alpha.paste(binary, (pad, pad))
    canvas.putalpha(alpha)
    return canvas


def squircle_mask(size: int, n: float = 5.0, supersample: int = 4) -> Image.Image:
    """Superellipse |x|^n + |y|^n <= 1 — macOS-style squircle.

    Built row-by-row so we don't need numpy. Supersample then downscale for AA.
    """
    s = size * supersample
    half = s / 2.0
    mask = Image.new("L", (s, s), 0)
    px = mask.load()
    for y in range(s):
        dy = abs((y + 0.5 - half) / half) ** n
        if dy > 1.0:
            continue
        threshold = (1.0 - dy)
        for x in range(s):
            dx = abs((x + 0.5 - half) / half) ** n
            if dx <= threshold:
                px[x, y] = 255
    return mask.resize((size, size), Image.LANCZOS)


def macos_app_icon(src: Image.Image, size: int = 1024) -> Image.Image:
    """Black squircle with the YAK logo centered.

    Apple's macOS icon grid: squircle fits 824/1024 (~80%) of the canvas,
    leaving room for the system shadow. Logo content sits inside that square.
    """
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    sq_size = int(round(size * 0.824))
    offset = (size - sq_size) // 2

    mask = squircle_mask(sq_size)
    bg = Image.new("RGBA", (sq_size, sq_size), (0, 0, 0, 255))
    bg.putalpha(mask)
    canvas.paste(bg, (offset, offset), bg)

    cropped = trim_to_content(src)
    w, h = cropped.size
    inner_target = sq_size * 0.78
    scale = inner_target / max(w, h)
    new_w, new_h = max(1, int(round(w * scale))), max(1, int(round(h * scale)))
    logo = cropped.resize((new_w, new_h), Image.LANCZOS)

    lx = offset + (sq_size - new_w) // 2
    ly = offset + (sq_size - new_h) // 2
    canvas.paste(logo, (lx, ly), logo)
    return canvas


ICONSET_SIZES = [
    ("icon_16x16.png", 16),
    ("icon_16x16@2x.png", 32),
    ("icon_32x32.png", 32),
    ("icon_32x32@2x.png", 64),
    ("icon_128x128.png", 128),
    ("icon_128x128@2x.png", 256),
    ("icon_256x256.png", 256),
    ("icon_256x256@2x.png", 512),
    ("icon_512x512.png", 512),
    ("icon_512x512@2x.png", 1024),
]


def main() -> None:
    src = Image.open(SOURCE).convert("RGBA")

    # Target menu-bar height: ~22pt. Output 1x at 22px tall, @2x at 44px.
    white_template(src, 22).save(ICON_DIR / "tray-template.png")
    white_template(src, 44).save(ICON_DIR / "tray-template@2x.png")

    icon1024 = macos_app_icon(src, 1024)
    icon1024.save(ICON_DIR / "macos-icon-1024.png")

    iconset_dir = ICON_DIR / "icon.iconset"
    iconset_dir.mkdir(exist_ok=True)
    for name, size in ICONSET_SIZES:
        icon1024.resize((size, size), Image.LANCZOS).save(iconset_dir / name)
    print("Wrote tray-template{,@2x}.png, macos-icon-1024.png, icon.iconset/*")


if __name__ == "__main__":
    main()
