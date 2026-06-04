import sys
from PIL import Image, ImageDraw

img = Image.new('RGB', (400, 80), (255, 255, 255))
draw = ImageDraw.Draw(img)
draw.text((20, 20), 'The quick brown fox', fill=(0, 0, 0))
img.save('ocr_benchmark/probe_surya_synth.png')

from surya.recognition import RecognitionPredictor

try:
    rec = RecognitionPredictor()
    print("Running RecognitionPredictor without detection bboxes...")
    rec_results = rec([img])
    print(f"Result type: {type(rec_results[0]).__name__}")
    print(f"Text lines count: {len(rec_results[0].text_lines)}")
    if rec_results[0].text_lines:
        print("Text:", rec_results[0].text_lines[0].text)
except Exception as e:
    import traceback
    traceback.print_exc()
