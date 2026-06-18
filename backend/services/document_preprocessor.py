import os
import re
import time
import logging
import pypdf
import cv2
import numpy as np
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Any, Tuple
import psutil

logger = logging.getLogger(__name__)

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

# ─────────────────────────────────────────────────────────────────────────────
# Memory and Sizing Guards
# ─────────────────────────────────────────────────────────────────────────────
def _check_memory_before_render(pages_to_render: int, target_dpi: int):
    """Prevents worker memory starvation before kicking off expensive page matrix calculations."""
    estimated_mb = pages_to_render * 30 * (target_dpi / 72) ** 2
    available_mb = psutil.virtual_memory().available / (1024 * 1024)
    if estimated_mb > available_mb * 0.70:
        raise MemoryError(
            f"Preprocess matrix calculation requires ~{estimated_mb:.0f}MB, but only {available_mb:.0f}MB is available."
        )

# ─────────────────────────────────────────────────────────────────────────────
# Spatial Evaluation Analytics
# ─────────────────────────────────────────────────────────────────────────────
def analyze_image_spatial_quality(image_np: np.ndarray) -> Tuple[float, float, float]:
    """
    Computes spatial profile metrics from a raw page array.
    Returns: (blur_variance, low_contrast_ratio, edge_density)
    """
    # Ensure image is in grayscale
    if len(image_np.shape) == 3:
        gray = cv2.cvtColor(image_np, cv2.COLOR_BGR2GRAY)
    else:
        gray = image_np

    # 1. Blur evaluation using modified Laplacian Variance
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()

    # 2. Contrast evaluation using standard deviation normalization
    h, w = gray.shape
    total_pixels = h * w
    std_dev = np.std(gray)
    
    # 3. Structural Edge density profile
    edges = cv2.Canny(gray, 50, 150)
    edge_pixels = np.sum(edges > 0)
    edge_density = (edge_pixels / total_pixels) * 100.0

    return float(laplacian_var), float(std_dev), float(edge_density)

# ─────────────────────────────────────────────────────────────────────────────
# Ingestion Analysis Report Model
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class PreprocessingReport:
    document_type: str = "DIGITAL"            # DIGITAL, SCANNED, HANDWRITTEN, MIXED
    routing_action: str = "DIRECT_PARSE"       # DIRECT_PARSE, VLM_ENHANCE_ROUTE
    parse_method_hint: str = "pypdf"
    extractable_text_ratio: float = 0.0
    average_blur_score: float = 0.0
    average_contrast_score: float = 0.0
    average_edge_density: float = 0.0
    handwritten_confidence: float = 0.0
    needs_enhancement: bool = False
    used_enhancement: bool = False
    enhancement_flags: dict = field(default_factory=lambda: {
        "needs_deskew": False,
        "needs_upscale": False,
        "needs_denoise": False,
        "needs_contrast_fix": False
    })
    timings: dict = field(default_factory=dict)

# ─────────────────────────────────────────────────────────────────────────────
# Primary Preprocessor Gate Class
# ─────────────────────────────────────────────────────────────────────────────
class DocumentPreprocessor:
    def __init__(self, file_path: str):
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Target ingestion artifact not found at: {file_path}")
        self.file_path = file_path
        self.filename = os.path.basename(file_path)

    def generate_routing_report(self) -> PreprocessingReport:
        """
        Inspects the file layer properties and spatial profiles to determine 
        if the file can be parsed directly or must be re-routed to the local VLM pipeline.
        """
        t_start = time.perf_counter()
        report = PreprocessingReport()
        
        # 1. Inspect format structures
        ext = os.path.splitext(self.filename)[-1].lower()
        if ext not in [".pdf", ".txt"]:
            # If it's a raw photo/image asset, force a VLM routing step immediately
            report.document_type = "SCANNED"
            report.routing_action = "VLM_ENHANCE_ROUTE"
            report.parse_method_hint = "vlm_local_api"
            report.timings["precheck_duration"] = time.perf_counter() - t_start
            return report

        if ext == ".txt":
            report.document_type = "DIGITAL"
            report.routing_action = "DIRECT_PARSE"
            report.parse_method_hint = "raw_text"
            report.timings["precheck_duration"] = time.perf_counter() - t_start
            return report

        # 2. Inspect PDF structural data layers
        try:
            with open(self.file_path, "rb") as f:
                reader = pypdf.PdfReader(f)
                total_pages = len(reader.pages)
                
                # Sample up to configured boundaries
                sample_limit = min(total_pages, getattr(config, "PREPROCESS_SAMPLE_PAGES", 5))
                text_chars_extracted = 0
                empty_pages_count = 0

                for i in range(sample_limit):
                    page_text = reader.pages[i].extract_text() or ""
                    cleaned_text = page_text.strip()
                    text_chars_extracted += len(cleaned_text)
                    if len(cleaned_text) < 20:
                        empty_pages_count += 1

                # Calculate extractable ratio indicators
                report.extractable_text_ratio = text_chars_extracted / (sample_limit if sample_limit > 0 else 1)
        except Exception as err:
            logger.error(f"Error reading PDF data layers: {err}")
            report.document_type = "SCANNED"
            report.routing_action = "VLM_ENHANCE_ROUTE"
            report.parse_method_hint = "vlm_local_api"
            return report

        # 3. Render Sample Array Matrices for Spatial Validation
        blur_accum, contrast_accum, edge_accum = [], [], []
        
        try:
            # Conditionally attempt to import pdf2image to evaluate image frames
            from pdf2image import convert_from_path
            
            target_dpi = getattr(config, "PREPROCESS_TARGET_DPI", 150)
            _check_memory_before_render(sample_limit, target_dpi)
            
            images = convert_from_path(self.file_path, first_page=1, last_page=sample_limit, dpi=target_dpi)
            
            for img in images:
                img_np = np.array(img)
                blur_v, contrast_v, edge_v = analyze_image_spatial_quality(img_np)
                blur_accum.append(blur_v)
                contrast_accum.append(contrast_v)
                edge_accum.append(edge_v)

            if blur_accum:
                report.average_blur_score = sum(blur_accum) / len(blur_accum)
                report.average_contrast_score = sum(contrast_accum) / len(contrast_accum)
                report.average_edge_density = sum(edge_accum) / len(edge_accum)

        except (ImportError, Exception) as render_err:
            logger.warning(f"Spatial image extraction engine bypassed or missing: {render_err}")
            # Fallback to structural estimation metrics if images can't render
            report.average_blur_score = 500.0 if empty_pages_count > 0 else 1000.0
            report.average_contrast_score = 50.0

        # 4. Execute Route Evaluation Decision
        # Threshold Flags
        is_text_layer_missing = report.extractable_text_ratio < 30.0
        is_heavy_scanned_profile = report.average_blur_score < 300.0 and report.average_contrast_score < 40.0
        has_high_empty_signature = empty_pages_count > (sample_limit * 0.4)

        # Route Flag Consolidation
        if is_text_layer_missing or is_heavy_scanned_profile or has_high_empty_signature:
            report.document_type = "SCANNED"
            report.routing_action = "VLM_ENHANCE_ROUTE"
            report.parse_method_hint = "vlm_local_api"
            
            # Setup recovery/enhancement directives
            if report.average_blur_score < 200.0:
                report.enhancement_flags["needs_denoise"] = True
            if report.average_contrast_score < 35.0:
                report.enhancement_flags["needs_contrast_fix"] = True
            report.needs_enhancement = True
        else:
            report.document_type = "DIGITAL"
            report.routing_action = "DIRECT_PARSE"
            report.parse_method_hint = "pypdf"

        report.timings["total_preprocessing_duration"] = time.perf_counter() - t_start
        return report

# ─────────────────────────────────────────────────────────────────────────────
# Local VLM Orchestration Connector Engine
# ─────────────────────────────────────────────────────────────────────────────
def execute_vlm_extraction_step(file_path: str, pipeline_id: int) -> str:
    """
    Acts as the target VLM API pipeline execution node.
    Converts document pages to images, sends them directly to the local open-source VLM engine,
    and consolidates the verified clean text extraction for downstream ingestion blocks.
    """
    logger.info(f"[VLM_ROUTER] Starting local open-source VLM processing pipeline context for: {file_path}")
    
    # 1. Target the local OpenAI-Compatible inference server endpoint mapping (vLLM or Ollama backend)
    vlm_endpoint = os.getenv("LOCAL_VLM_ENDPOINT", "http://localhost:11434/v1/chat/completions")
    vlm_model_name = os.getenv("LOCAL_VLM_MODEL", "qwen2-vl:7b")
    
    from pdf2image import convert_from_path
    import base64

    try:
        # Render pages for vision context window ingestion
        images = convert_from_path(file_path, dpi=150)
        consolidated_text_output = []

        for idx, img in enumerate(images):
            # Encode image to base64 format string
            _, buffer = cv2.imencode('.png', cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR))
            base64_image = base64.b64encode(buffer).decode('utf-8')

            # Build structural request schema payloads matching standard multimodal API layout
            payload = {
                "model": vlm_model_name,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text", 
                                "text": "Transcribe this document page layout completely. Preserve headings, sections, text structural formatting, and all written content directly into clean markdown format text. Do not summarize or emit conversational commentary."
                            },
                            {
                                "type": "image_url", 
                                "image_url": {"url": f"data:image/png;base64,{base64_image}"}
                            }
                        ]
                    }
                ],
                "temperature": 0.1
            }

            headers = {"Content-Type": "application/json"}
            
            logger.info(f"[VLM_ROUTER] Querying VLM for page {idx + 1}/{len(images)}...")
            response = requests.post(vlm_endpoint, headers=headers, data=json.dumps(payload), timeout=120)
            
            if response.status_code == 200:
                result_data = response.json()
                page_markdown = result_data["choices"][0]["message"]["content"]
                consolidated_text_output.append(page_markdown)
            else:
                logger.error(f"[VLM_ROUTER] Failed page transcription at index {idx}. Status: {response.status_code}")
                # Fallback to local text framework on exception blocks
                continue

        return "\n\n<--- PAGE_BREAK --->\n\n".join(consolidated_text_output)

    except Exception as e:
        logger.critical(f"[VLM_ROUTER] Fatal validation crash inside VLM execution routine: {e}")
        raise RuntimeError(f"VLM pipeline transcription failed: {e}")