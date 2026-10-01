"""Generate binary fixtures for the mobile/backend live-integration pass."""
from pathlib import Path

from PIL import Image

out = Path(__file__).resolve().parent / 'fixtures'
out.mkdir(exist_ok=True)

# Small valid PNG (OCR engine is absent in this env, so live calls using this
# file are expected to reach the OCR stage and return 503 ocr_unavailable —
# which is itself one of the paths under test).
Image.new('RGB', (200, 100), color='white').save(out / 'valid.png')

# Uncompressible noise BMP guaranteed to exceed the 10 MiB image limit.
noise = Image.effect_noise((2100, 2100), 128).convert('RGB')
noise.save(out / 'oversized.bmp')
for name in ('valid.png', 'oversized.bmp'):
    size = (out / name).stat().st_size
    print(f'{name}: {size} bytes')
