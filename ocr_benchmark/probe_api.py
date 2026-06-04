"""Quick probe to inspect Surya and PaddleOCR API return types."""
import sys
from PIL import Image, ImageDraw

# Make synthetic image
img = Image.new('RGB', (400, 80), (255,255,255))
draw = ImageDraw.Draw(img)
draw.text((20, 25), 'hello world test', fill=(0,0,0))
img.save('ocr_benchmark/probe_test.png')
print("Synthetic image created.")

# ── Surya probe ───────────────────────────────────────────────────────────────
print('\n--- Surya probe ---')
try:
    from surya.recognition import RecognitionPredictor
    from surya.detection import DetectionPredictor
    det = DetectionPredictor()
    rec = RecognitionPredictor()
    det_res = det([img])
    print('det_res[0] type:', type(det_res[0]).__name__)
    print('bboxes count:', len(det_res[0].bboxes))
    if det_res[0].bboxes:
        b0 = det_res[0].bboxes[0]
        print('bbox[0] type:', type(b0).__name__)
        print('bbox[0] dir:', [x for x in dir(b0) if not x.startswith('_')])
        print('bbox[0] value:', b0.bbox if hasattr(b0, 'bbox') else b0)
    # Test recognition with full-page bbox
    bboxes = [[0, 0, img.width, img.height]]
    rec_res = rec([img], [bboxes])
    print('rec_res[0] type:', type(rec_res[0]).__name__)
    tls = rec_res[0].text_lines
    print('text_lines count:', len(tls))
    if tls:
        tl0 = tls[0]
        print('text_line[0] type:', type(tl0).__name__)
        print('text_line[0] attrs:', [x for x in dir(tl0) if not x.startswith('_')])
        print('text_line[0].text:', getattr(tl0, 'text', None))
    else:
        print('text_lines is EMPTY — recognition returned nothing with full-page bbox')
        # Try detected bboxes if any
        if det_res[0].bboxes:
            real_bboxes = [b.bbox for b in det_res[0].bboxes]
            rec_res2 = rec([img], [real_bboxes])
            print('Retry with detected bboxes:', len(rec_res2[0].text_lines), 'lines')
except Exception as e:
    import traceback; traceback.print_exc()

# ── PaddleOCR probe ───────────────────────────────────────────────────────────
print('\n--- PaddleOCR probe ---')
try:
    import logging
    logging.getLogger('ppocr').setLevel(logging.ERROR)
    logging.getLogger('paddle').setLevel(logging.ERROR)
    from paddleocr import PaddleOCR
    ocr = PaddleOCR(use_angle_cls=True, lang='en')
    result = ocr.ocr('ocr_benchmark/probe_test.png', cls=True)
    print('result type:', type(result).__name__)
    print('result:', result)
    if result:
        print('result[0] type:', type(result[0]).__name__ if result[0] else 'None')
        if result[0]:
            print('result[0][0] type:', type(result[0][0]).__name__)
            print('result[0][0]:', result[0][0])
except Exception as e:
    import traceback; traceback.print_exc()

print('\nProbe complete.')
