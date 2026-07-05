import os
import sys
import time
import logging
from PIL import Image

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytesseract
from pytesseract import Output
import cv2
import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO)

from services.pdf_parser import render_document_pages

def benchmark_ocr():
    filepath = r"d:\Projects\task-schedular\backend\storage\uploads\176_PBL_Patent.pdf"
    if not os.path.exists(filepath):
        print(f"Error: PDF not found at {filepath}")
        return

    print("=" * 80)
    print("OCR BENCHMARK FOR DIGITAL PATENT PDFS")
    print("=" * 80)

    # 1. Benchmark different render DPIs
    dpis = [300, 400, 450, 600]
    for dpi in dpis:
        start_time = time.perf_counter()
        try:
            images = render_document_pages(filepath, max_pages=1, dpi=dpi)
            if not images:
                print(f"DPI {dpi}: Render failed (no images)")
                continue
            img = images[0]
            w, h = img.size
            duration = time.perf_counter() - start_time
            print(f"DPI {dpi}: Rendered successfully | Size: {w}x{h} | Time: {duration:.2f}s | Mode: {img.mode}")
        except Exception as e:
            print(f"DPI {dpi}: Render failed with exception: {e}")

    # Load image at optimal 300 DPI for subsequent tests
    print("\nLoading base image at 300 DPI for segmentation & preprocessing benchmarks...")
    img_300 = render_document_pages(filepath, max_pages=1, dpi=300)[0]
    w_300, h_300 = img_300.size

    # Convert to OpenCV image for preprocessing
    open_cv_image = np.array(img_300)
    # Convert RGB to BGR
    if len(open_cv_image.shape) == 3:
        open_cv_image = open_cv_image[:, :, ::-1].copy()

    # Preprocessing pipelines
    preprocessed_images = {
        "original": open_cv_image,
        "grayscale": cv2.cvtColor(open_cv_image, cv2.COLOR_BGR2GRAY),
    }

    # Otsu threshold
    gray = preprocessed_images["grayscale"]
    _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    preprocessed_images["otsu_threshold"] = otsu

    # Adaptive threshold
    adaptive = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
    preprocessed_images["adaptive_threshold"] = adaptive

    # Denoise + Otsu
    denoised = cv2.fastNlMeansDenoising(gray, h=3)
    _, denoised_otsu = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    preprocessed_images["denoise_otsu"] = denoised_otsu

    # 2. Run Tesseract configuration benchmarks
    psms = [3, 4, 6]
    preprocessors = ["original", "grayscale", "otsu_threshold", "adaptive_threshold", "denoise_otsu"]

    print("\n" + "-" * 50)
    print("RUNNING TESSERACT BENCHMARKS (PSM vs PREPROCESSING)")
    print("-" * 50)

    for psm in psms:
        for prep_name in preprocessors:
            prep_img = preprocessed_images[prep_name]
            
            # Convert OpenCV back to PIL for pytesseract
            if len(prep_img.shape) == 2:
                pil_prep = Image.fromarray(prep_img)
            else:
                pil_prep = Image.fromarray(cv2.cvtColor(prep_img, cv2.COLOR_BGR2RGB))

            start_t = time.perf_counter()
            config_str = f"--psm {psm} --oem 3"
            try:
                data = pytesseract.image_to_data(pil_prep, output_type=Output.DICT, config=config_str)
                duration = time.perf_counter() - start_t
                
                # Compute metrics
                texts = [data['text'][i].strip() for i in range(len(data['level'])) if data['level'][i] == 5]
                words = [w for w in texts if w]
                text_content = " ".join(words)
                
                char_count = len(text_content)
                word_count = len(words)
                unique_words = len(set([w.lower() for w in words]))
                
                confidences = [int(data['conf'][i]) for i in range(len(data['level'])) if data['level'][i] == 5 and data['conf'][i] != '-1']
                avg_conf = np.mean(confidences) if confidences else 0.0
                
                printable_chars = sum(1 for c in text_content if c.isprintable())
                printable_ratio = (printable_chars / char_count) if char_count > 0 else 0.0

                # Reading order check (checking if important phrases are contiguous or jumbled)
                has_inventor = "Kaustav" in text_content and "Kumar" in text_content
                inventor_index_k = text_content.find("Kaustav")
                inventor_index_u = text_content.find("Kumar")
                is_jumbled = abs(inventor_index_k - inventor_index_u) > 30 if (inventor_index_k != -1 and inventor_index_u != -1) else True

                print(f"PSM {psm} | Prep: {prep_name:18} | Words: {word_count:4} | Unique: {unique_words:4} | Conf: {avg_conf:5.1f}% | Time: {duration:.2f}s | Jumbled: {is_jumbled} | CharCount: {char_count:5}")
            except Exception as e:
                print(f"PSM {psm} | Prep: {prep_name:18} | Failed: {e}")

if __name__ == "__main__":
    benchmark_ocr()
