from PIL import Image, ImageDraw, ImageFilter

# Create high-res image with transparent background
size = 1024
img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

# Premium metallic blue colors
base_blue = (0, 102, 255)
light_blue = (77, 155, 255)
bright_blue = (153, 204, 255)
dark_blue = (0, 61, 184)

# Stroke width for clean, professional look
stroke_width = int(size * 0.12)  # 12% of size

# Calculate V shape points - symmetric and centered
top_y = size * 0.15
bottom_y = size * 0.85
left_x = size * 0.22
right_x = size * 0.78
center_x = size * 0.50

# Draw main V shape with thick, smooth strokes
# Left stroke
left_points = [
    (left_x, top_y),
    (left_x + stroke_width, top_y),
    (center_x + stroke_width/2, bottom_y),
    (center_x - stroke_width/2, bottom_y)
]
draw.polygon(left_points, fill=base_blue)

# Right stroke
right_points = [
    (right_x, top_y),
    (right_x - stroke_width, top_y),
    (center_x - stroke_width/2, bottom_y),
    (center_x + stroke_width/2, bottom_y)
]
draw.polygon(right_points, fill=base_blue)

# Add smooth metallic gradient overlay on left stroke
gradient_overlay = Image.new('RGBA', (size, size), (0, 0, 0, 0))
grad_draw = ImageDraw.Draw(gradient_overlay)

# Left highlight
left_highlight = [
    (left_x + stroke_width * 0.15, top_y + size * 0.03),
    (left_x + stroke_width * 0.45, top_y + size * 0.03),
    (center_x + stroke_width * 0.15, bottom_y - size * 0.05),
    (center_x - stroke_width * 0.15, bottom_y - size * 0.05)
]
grad_draw.polygon(left_highlight, fill=light_blue)

# Right highlight
right_highlight = [
    (right_x - stroke_width * 0.15, top_y + size * 0.03),
    (right_x - stroke_width * 0.45, top_y + size * 0.03),
    (center_x - stroke_width * 0.15, bottom_y - size * 0.05),
    (center_x + stroke_width * 0.15, bottom_y - size * 0.05)
]
grad_draw.polygon(right_highlight, fill=light_blue)

# Bright shine edge on left
left_shine = [
    (left_x + stroke_width * 0.25, top_y + size * 0.05),
    (left_x + stroke_width * 0.35, top_y + size * 0.05),
    (center_x, bottom_y - size * 0.15),
    (center_x - stroke_width * 0.05, bottom_y - size * 0.15)
]
grad_draw.polygon(left_shine, fill=bright_blue + (200,))

# Apply slight blur for smooth metallic effect
img = Image.alpha_composite(img, gradient_overlay)
img = img.filter(ImageFilter.SMOOTH)

# Resize to 512x512 with high-quality antialiasing
img_final = img.resize((512, 512), Image.Resampling.LANCZOS)

# Save the icon
img_final.save('d:/Valido/valido-icon.png')
print('✓ Premium metallic V icon created!')
print(f'  Size: 512x512px')
print(f'  Mode: {img_final.mode}')
print(f'  Transparent background: Yes')
