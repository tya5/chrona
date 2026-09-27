"""Rebuild the documented same-scale PNG comparison boards."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
OUT = HERE / "comparison"
FONT = REPO / "src/chrona/resources/fonts/noto-sans-bold-v1.ttf"


def board(left_path: Path, right_path: Path, right_title: str, output: str) -> None:
    left = Image.open(left_path).convert("RGB")
    right = Image.open(right_path).convert("RGB")
    if left.width != right.width:
        raise ValueError(f"comparison panels must have matching width: {left.width} != {right.width}")
    heading_height = 54
    canvas = Image.new("RGB", (left.width * 2, max(left.height, right.height) + heading_height), "#d8d8d8")
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype(str(FONT), 24)
    draw.text((12, 12), "Chrona bundled default", fill="#20242b", font=font)
    draw.text((left.width + 12, 12), right_title, fill="#20242b", font=font)
    canvas.paste(left, (0, heading_height))
    canvas.paste(right, (left.width, heading_height))
    canvas.save(OUT / output, optimize=True)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    starter = HERE / "starter/default.png"
    halcyon = HERE / "halcyon-1/default.png"
    reference = HERE / "13-gallery-editorial/reference.png"
    board(halcyon, reference, "13-gallery-editorial", "halcyon-vs-editorial.png")
    board(starter, reference, "13-gallery-editorial — full figure", "starter-vs-editorial.png")
    reference_image = Image.open(reference).convert("RGB")
    starter_image = Image.open(starter).convert("RGB")
    top = reference_image.crop((0, 0, reference_image.width, starter_image.height))
    crop_path = OUT / "editorial-top.png"
    top.save(crop_path, optimize=True)
    board(starter, crop_path, "13-gallery-editorial — top 900 px crop", "starter-vs-editorial-top.png")


if __name__ == "__main__":
    main()
