from PIL import Image, ImageDraw, ImageFont
import os

# Create main favicon (64x64)
img = Image.new('RGB', (64, 64), color='#007bff')
draw = ImageDraw.Draw(img)

# Draw white circle background
draw.ellipse([8, 8, 56, 56], fill='white')

# Add "JM" text
font_path = 'C:/Windows/Fonts/arial.ttf'
if os.path.exists(font_path):
    font = ImageFont.truetype(font_path, 24)
    draw.text((32, 32), 'JM', fill='#007bff', anchor='mm', font=font)
else:
    # Fallback without font
    draw.text((20, 20), 'JM', fill='#007bff')

# Save as ICO
img.save('sendmail/static/favicon.ico', format='ICO', sizes=[(16,16), (32,32), (64,64)])

# Save PNG versions
img_16 = img.resize((16, 16), Image.Resampling.LANCZOS)
img_16.save('sendmail/static/favicon-16x16.png')

img_32 = img.resize((32, 32), Image.Resampling.LANCZOS)
img_32.save('sendmail/static/favicon-32x32.png')

# Create Apple Touch Icon (180x180)
img_180 = Image.new('RGB', (180, 180), color='#007bff')
draw_180 = ImageDraw.Draw(img_180)
draw_180.ellipse([20, 20, 160, 160], fill='white')
if os.path.exists(font_path):
    font_large = ImageFont.truetype(font_path, 72)
    draw_180.text((90, 90), 'JM', fill='#007bff', anchor='mm', font=font_large)
img_180.save('sendmail/static/apple-touch-icon.png')

print('✅ Favicon created successfully!')
print('   - favicon.ico (16x16, 32x32, 64x64)')
print('   - favicon-16x16.png')
print('   - favicon-32x32.png')
print('   - apple-touch-icon.png (180x180)')
