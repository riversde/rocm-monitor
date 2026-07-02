#!/usr/bin/env python3
"""Generate a 256x256 icon for the app."""

from PIL import Image, ImageDraw, ImageFont
import io

# Create a 256x256 image
size = 256
img = Image.new("RGBA", (size, size), (10, 14, 23, 255))  # dark navy background
draw = ImageDraw.Draw(img)

# Draw a circle (GPU chip shape)
cx, cy = size // 2, size // 2
r = 100
draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(26, 42, 70, 255), outline=(0, 198, 255, 255), width=4)

# Draw a smaller inner circle
r2 = 60
draw.ellipse([cx - r2, cy - r2, cx + r2, cy + r2], fill=(10, 14, 23, 255), outline=(0, 198, 255, 200), width=3)

# Draw a lightning bolt / chip symbol in the center
draw.polygon([
    (cx + 10, cy - 30),
    (cx - 20, cy + 5),
    (cx - 5, cy + 5),
    (cx - 15, cy + 30),
    (cx + 20, cy - 5),
    (cx + 5, cy - 5),
], fill=(0, 198, 255, 255))

# Save as PNG (electron-builder accepts PNG for icon)
img.save("build/icon.png")
print(f"Created build/icon.png ({size}x{size})")
