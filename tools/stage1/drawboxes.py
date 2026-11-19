"""Draw every sampled box from fresco_samples.json on the 3840 scan, numbered, plus the vault unroll region."""
import json, os
from PIL import Image, ImageDraw
d = json.load(open('fresco_samples.json'))
im = Image.open(os.environ.get('FRESCO_3840', 'reference/download/athens-3840.jpg')).convert('RGB')
dr = ImageDraw.Draw(im)
seen = {}
for name, v in d.items():
    b = v.get('box_3840')
    if not b or tuple(b) in seen:
        continue
    seen[tuple(b)] = len(seen) + 1
    dr.rectangle(b, outline=(0, 255, 0), width=4)
    dr.text((b[2] + 6, b[1]), str(seen[tuple(b)]), fill=(0, 255, 0))
im.resize((1920, 1330)).save('crops/sample-boxes.jpg', quality=88)
for b, n in seen.items(): print(n, b, [k for k, v in d.items() if tuple(v.get('box_3840') or ()) == b])
