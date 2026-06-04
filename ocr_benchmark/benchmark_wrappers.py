import time
import os
import psutil

def get_memory():
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024

class TesseractWrapper:
    def __init__(self):
        import pytesseract
        self.pytesseract = pytesseract

    def extract_text(self, image_path: str):
        t0 = time.perf_counter()
        mem_before = get_memory()
        from PIL import Image
        img = Image.open(image_path)
        text = self.pytesseract.image_to_string(img)
        t1 = time.perf_counter()
        mem_after = get_memory()
        return {
            "text": text,
            "latency_s": t1 - t0,
            "memory_mb": max(0, mem_after - mem_before)
        }

class PaddleWrapper:
    def __init__(self):
        import logging
        import warnings
        warnings.filterwarnings('ignore')
        logging.getLogger('ppocr').setLevel(logging.ERROR)
        logging.getLogger('paddle').setLevel(logging.ERROR)
        from paddleocr import PaddleOCR
        # v3 API: use_angle_cls deprecated, use use_textline_orientation
        self.ocr = PaddleOCR(lang='en')
        # Probe that inference actually works (oneDNN backend may be broken)
        self._functional = self._probe_functional()

    def _probe_functional(self) -> bool:
        from PIL import Image, ImageDraw
        import tempfile, os
        probe_img = Image.new('RGB', (200, 40), (255, 255, 255))
        ImageDraw.Draw(probe_img).text((5, 10), 'test', fill=(0, 0, 0))
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            probe_img.save(f.name)
            tmp = f.name
        try:
            list(self.ocr.predict(tmp))
            return True
        except Exception:
            return False
        finally:
            try: os.unlink(tmp)
            except Exception: pass

    def extract_text(self, image_path: str):
        t0 = time.perf_counter()
        mem_before = get_memory()
        text = ""
        if self._functional:
            try:
                results = list(self.ocr.predict(image_path))
                lines = []
                for res in results:
                    # v3 returns objects with rec_texts attribute
                    if hasattr(res, 'rec_texts'):
                        lines.extend(res.rec_texts or [])
                    elif hasattr(res, '__iter__'):
                        for item in res:
                            if isinstance(item, (list, tuple)) and len(item) >= 2:
                                txt = item[1]
                                if isinstance(txt, (list, tuple)): txt = txt[0]
                                lines.append(str(txt))
                text = "\n".join(str(l) for l in lines if l)
            except Exception as e:
                text = f"ERROR: {e}"
        t1 = time.perf_counter()
        mem_after = get_memory()
        return {
            "text": text,
            "latency_s": t1 - t0,
            "memory_mb": max(0, mem_after - mem_before)
        }

class EasyOCRWrapper:
    def __init__(self):
        import easyocr
        import warnings
        warnings.filterwarnings('ignore', category=UserWarning)
        self.reader = easyocr.Reader(['en'], verbose=False)
        
    def extract_text(self, image_path: str):
        t0 = time.perf_counter()
        mem_before = get_memory()
        result = self.reader.readtext(image_path, detail=0)
        text = "\n".join(result)
        t1 = time.perf_counter()
        mem_after = get_memory()
        return {
            "text": text,
            "latency_s": t1 - t0,
            "memory_mb": max(0, mem_after - mem_before)
        }

class DocTRWrapper:
    def __init__(self):
        os.environ['USE_TORCH'] = '1'
        from doctr.models import ocr_predictor
        self.model = ocr_predictor(pretrained=True)
        
    def extract_text(self, image_path: str):
        t0 = time.perf_counter()
        mem_before = get_memory()
        from doctr.io import DocumentFile
        doc = DocumentFile.from_images(image_path)
        result = self.model(doc)
        text = result.render()
        t1 = time.perf_counter()
        mem_after = get_memory()
        return {
            "text": text,
            "latency_s": t1 - t0,
            "memory_mb": max(0, mem_after - mem_before)
        }

class SuryaWrapper:
    def __init__(self):
        # We initialize both, but RecognitionPredictor will fail on call if llama-server isn't installed.
        # So we catch it at extract_text time.
        from surya.recognition import RecognitionPredictor
        from surya.detection import DetectionPredictor
        self.det_predictor = DetectionPredictor()
        self.rec_predictor = RecognitionPredictor()

    def extract_text(self, image_path: str):
        t0 = time.perf_counter()
        mem_before = get_memory()
        from PIL import Image
        img = Image.open(image_path).convert("RGB")

        # Downscale very large images to avoid CPU OOM on 300 DPI pages
        max_side = 1500
        if max(img.width, img.height) > max_side:
            scale = max_side / max(img.width, img.height)
            img = img.resize((int(img.width * scale), int(img.height * scale)), Image.LANCZOS)

        # Run detection — returns list of TextDetectionResult objects
        det_results = self.det_predictor([img])

        try:
            # Pass TextDetectionResult objects directly to recognition predictor.
            # The rec API expects det_results, not raw coordinate lists.
            rec_results = self.rec_predictor([img], det_results)
            text = "\n".join([r.text for r in rec_results[0].text_lines])
        except Exception as e:
            text = f"ERROR: {e.__class__.__name__}: {str(e)[:100]}"

        t1 = time.perf_counter()
        mem_after = get_memory()
        return {
            "text": text,
            "latency_s": t1 - t0,
            "memory_mb": max(0, mem_after - mem_before)
        }
