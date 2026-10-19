from PIL import Image, ImageOps, ImageFilter, ImageEnhance
import numpy as np

im = Image.open('test_crop1.jpg').convert('RGB')
arr = np.array(im, dtype=np.float32)
r, g, b = arr[:,:,0], arr[:,:,1], arr[:,:,2]

h, w, _ = arr.shape
Y, X = np.mgrid[:h, :w]

# Initialize mask with 1 (subject)
mask = np.ones((h, w), dtype=np.float32)

# 1. Cyan background (top-right)
cyan = (b > 130) & (b > r + 15)
mask[cyan] = 0.0

# 2. Tuxedo and person on the right
tux = (X > 420) & (r < 90) & (g < 90) & (b < 90)
mask[tux] = 0.0
person_r = (X > 465)
mask[person_r] = 0.0

# 3. Person on the left
person_l = (X < 125)
mask[person_l] = 0.0
# Checked shirt
shirt_l = (X < 155) & (Y > 240) & (r > g) & (r > 65)
mask[shirt_l] = 0.0

# 4. Outer margins (oval)
dist_center = np.sqrt(((X - 300) / 225.0)**2 + ((Y - 300) / 260.0)**2)
mask[dist_center > 1.0] = 0.0

# Smooth the mask boundary
mask_im = Image.fromarray((mask * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(6))
mask_smooth = np.array(mask_im, dtype=np.float32) / 255.0

# Convert to grayscale
gray = ImageOps.grayscale(im)
arr_gray = np.array(gray, dtype=np.float32)

# Apply contrast curve:
# We want clean highlights on skin (so Voronoi doesn't clutter face with dark dots)
# and deep blacks on hair, pupils, nostrils, mouth line, and collar
arr_norm = arr_gray / 255.0

# Tone mapping curve
arr_contrast = np.where(arr_norm > 0.60, 
                        1.0 - (1.0 - arr_norm) * 0.45,  # bright highlights
                        np.power(arr_norm / 0.60, 1.6) * 0.60) # darks pushed down
arr_contrast = np.clip(arr_contrast * 255.0, 0, 255)

# Enhance edges (unsharp mask for crisp stippling contours)
enh_im = Image.fromarray(arr_contrast.astype(np.uint8))
sharp_im = enh_im.filter(ImageFilter.UnsharpMask(radius=2, percent=200, threshold=2))
sharp_arr = np.array(sharp_im, dtype=np.float32)

# Blend with pure white background where mask is 0
final_arr = sharp_arr * mask_smooth + 255.0 * (1.0 - mask_smooth)
final_im = Image.fromarray(np.clip(final_arr, 0, 255).astype(np.uint8))

final_im.save('margarita_salas_bw.png')
print('margarita_salas_bw.png generated successfully!')
