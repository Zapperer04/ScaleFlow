"""Probe PaddleOCR v3 predict() return format."""
import logging
logging.getLogger('ppocr').setLevel(logging.ERROR)
logging.getLogger('paddle').setLevel(logging.ERROR)

from paddleocr import PaddleOCR
import warnings
warnings.filterwarnings('ignore')

ocr = PaddleOCR(lang='en')
result = ocr.predict('ocr_benchmark/probe_test.png')

print('result type:', type(result).__name__)
print('result len:', len(result) if result else 0)

if result:
    for i, item in enumerate(result):
        print(f'\nresult[{i}] type:', type(item).__name__)
        print(f'result[{i}] attrs:', [x for x in dir(item) if not x.startswith('_')])
        # Try common attributes
        for attr in ['rec_texts', 'rec_text', 'texts', 'text', 'rec_res', 'ocr_result', 'boxes', 'dt_boxes', 'predictions']:
            val = getattr(item, attr, None)
            if val is not None:
                print(f'  .{attr} = {val}')
        # Try dict access
        try:
            print(f'  dict keys: {list(item.keys())}')
        except Exception:
            pass
        # Try iteration
        try:
            for j, sub in enumerate(item):
                print(f'  item[{j}] type: {type(sub).__name__}, val: {sub}')
                if j > 2: break
        except Exception:
            pass

print('\nProbe complete.')
