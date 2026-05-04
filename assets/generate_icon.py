"""SVG → PNG → ICO 変換スクリプト (Pillow + cairosvg)
cairosvg が使えない場合は Pillow のみで桜アイコンを直接描画する。
"""
from __future__ import annotations
import sys
from pathlib import Path

ASSETS_DIR = Path(__file__).resolve().parent
SVG_PATH = ASSETS_DIR / "noteforge_icon.svg"
PNG_PATH = ASSETS_DIR / "noteforge_icon.png"
ICO_PATH = ASSETS_DIR / "noteforge_icon.ico"


def build_via_cairosvg() -> bool:
    try:
        import cairosvg  # type: ignore
        from PIL import Image
        import io
        png_bytes = cairosvg.svg2png(url=str(SVG_PATH), output_width=256, output_height=256)
        img = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
        img.save(PNG_PATH, "PNG")
        # ICO: 複数サイズ
        sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
        icons = [img.resize(s) for s in sizes]
        icons[0].save(ICO_PATH, format="ICO", sizes=sizes, append_images=icons[1:])
        return True
    except Exception as e:
        print(f"cairosvg 変換失敗: {e}")
        return False


def build_via_pillow() -> None:
    """Pillow だけで桜花びら + N を描画して ICO 生成"""
    from PIL import Image, ImageDraw, ImageFont
    import math

    SIZE = 256
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    cx, cy = SIZE // 2, SIZE // 2

    # 花びら5枚
    petal_color = (255, 178, 210, 255)
    petal_border = (214, 77, 132, 255)
    for i in range(5):
        angle = math.radians(i * 72 - 90)
        px = cx + int(52 * math.cos(angle))
        py = cy + int(52 * math.sin(angle))
        draw.ellipse([px - 38, py - 38, px + 38, py + 38], fill=petal_color, outline=petal_border, width=3)

    # 中心円
    draw.ellipse([cx - 46, cy - 46, cx + 46, cy + 46], fill=(255, 250, 252, 255), outline=petal_border, width=4)

    # "N" テキスト
    font_size = 72
    font = None
    for name in ["segoeuib.ttf", "arial.ttf", "DejaVuSans-Bold.ttf"]:
        for d in [r"C:\Windows\Fonts", "/usr/share/fonts/truetype/dejavu"]:
            fp = Path(d) / name
            if fp.exists():
                try:
                    from PIL import ImageFont as _IF
                    font = _IF.truetype(str(fp), font_size)
                    break
                except Exception:
                    pass
        if font:
            break
    if font is None:
        from PIL import ImageFont as _IF
        font = _IF.load_default()

    text = "N"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    tx = cx - tw // 2 - bbox[0]
    ty = cy - th // 2 - bbox[1]
    draw.text((tx, ty), text, font=font, fill=(179, 33, 99, 255))

    img.save(PNG_PATH, "PNG")

    sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    icons = [img.resize(s, Image.LANCZOS) for s in sizes]
    icons[0].save(ICO_PATH, format="ICO", sizes=sizes, append_images=icons[1:])


if __name__ == "__main__":
    print(f"生成先: {ICO_PATH}")
    if not build_via_cairosvg():
        print("Pillow のみで描画します...")
        build_via_pillow()
    print(f"完了: {PNG_PATH}")
    print(f"完了: {ICO_PATH}")
