from PIL import Image
from surya.recognition import RecognitionPredictor
from surya.layout import LayoutPredictor

img = Image.new('RGB', (400, 80), (255, 255, 255))

try:
    layout = LayoutPredictor()
    rec = RecognitionPredictor()

    layout_res = layout([img])
    rec_res = rec([img], layout_res)
    print(rec_res[0].text_lines)
except Exception as e:
    import traceback
    traceback.print_exc()
