"""Probe Surya recognition output structure in detail."""
import sys
from PIL import Image, ImageDraw
import io

# Make synthetic image with clear black text on white
img = Image.new('RGB', (400, 80), (255, 255, 255))
draw = ImageDraw.Draw(img)
draw.text((20, 20), 'The quick brown fox', fill=(0, 0, 0))
img.save('ocr_benchmark/probe_surya_synth.png')

from surya.recognition import RecognitionPredictor
from surya.detection import DetectionPredictor

det = DetectionPredictor()
rec = RecognitionPredictor()

print('Running detection...')
det_results = det([img])
print(f'det_results type: {type(det_results[0]).__name__}')
print(f'bboxes count: {len(det_results[0].bboxes)}')
for i, b in enumerate(det_results[0].bboxes[:3]):
    print(f'  bbox[{i}]: {b.bbox}, polygon: {b.polygon[:2] if hasattr(b, "polygon") else "N/A"}')

print('\nRunning recognition with det_results...')
rec_results = rec([img], det_results)
print(f'rec_results type: {type(rec_results[0]).__name__}')
print(f'rec_results[0] attrs: {[a for a in dir(rec_results[0]) if not a.startswith("_")]}')
print(f'text_lines count: {len(rec_results[0].text_lines)}')

if rec_results[0].text_lines:
    for i, tl in enumerate(rec_results[0].text_lines[:3]):
        print(f'\ntext_line[{i}] type: {type(tl).__name__}')
        print(f'  attrs: {[a for a in dir(tl) if not a.startswith("_")]}')
        for attr in ['text', 'value', 'content', 'label', 'raw_text', 'confidence', 'bbox', 'polygon']:
            v = getattr(tl, attr, "NOT_FOUND")
            if v != "NOT_FOUND":
                print(f'  .{attr} = {repr(v)[:100]}')
else:
    print('text_lines is EMPTY!')
    print('\nRaw rec_results[0]:', repr(rec_results[0])[:300])

print('\nDone.')
