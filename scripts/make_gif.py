#!/usr/bin/env python3
"""Stitch screenshots into an animated GIF for the README."""

from PIL import Image as PILImage
import imageio.v3 as iio
import numpy as np
from pathlib import Path

SRC_DIR = Path(__file__).parent.parent / "GIF images"
OUT_DIR = Path(__file__).parent.parent / "screenshots"
OUT_FILE = OUT_DIR / "demo.gif"

files = sorted(SRC_DIR.glob("*.png"))
if len(files) < 2:
    raise ValueError(f"Need at least 2 screenshots, found {len(files)}")

base_w = 800
bg_color = (10, 14, 23)

# First pass: compute uniform height
max_h = 0
for f in files:
    with PILImage.open(str(f)) as img:
        h = int(img.height * base_w / img.width)
        if h > max_h:
            max_h = h

# Second pass: resize + pad to uniform size
resized = []
for f in files:
    with PILImage.open(str(f)).convert("RGB") as pil:
        new_w = base_w
        new_h = int(pil.height * new_w / pil.width)
        resized_img = pil.resize((new_w, new_h), PILImage.LANCZOS)
        padded = PILImage.new("RGB", (base_w, max_h), bg_color)
        padded.paste(resized_img, (0, 0))
        resized.append(np.array(padded))

# Repeat frames for smooth animation
fps = 10
repeats_per_frame = 5
all_frames = []
for img in resized:
    for _ in range(repeats_per_frame):
        all_frames.append(img)

iio.imwrite(
    str(OUT_FILE),
    all_frames,
    duration=1000 // fps,
    loop=0,
    quality=7,
    subrectangles=True,
)

print(f"Created {OUT_FILE} ({len(all_frames)} frames, {OUT_FILE.stat().st_size / 1024:.0f}KB)")
