import os
import sys
import json
import time

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from services.document_preprocessor import DocumentPreprocessor, _call_gemini_page_parser

# Setup target PDF
pdf_path = r"storage/uploads/178_PBL_Patent.pdf"

# Initialize preprocessor and render page 1
dp = DocumentPreprocessor(pdf_path)
images = dp.render_document(max_pages=1, dpi=300)
img = images[0]

# Retrieve API Key
from services.document_preprocessor import _get_gemini_api_key
api_key = _get_gemini_api_key()
print("API Key check:", bool(api_key))

import requests
from services.document_preprocessor import GEMINI_MODEL_NAME, GEMINI_API_URL_TEMPLATE, _pil_to_base64, _ensure_pil_image, _extract_gemini_text, _clean_json_text

# Run Experiment 1 (Current Prompt)
print("\n=== Running Experiment 1: Current Prompt ===")
t0 = time.perf_counter()
raw_text_1 = _call_gemini_page_parser(img, page_number=1, pipeline_id="exp1")
t1 = time.perf_counter()
duration_1 = t1 - t0
cleaned_1 = _clean_json_text(raw_text_1)
parsed_1 = json.loads(cleaned_1)

nodes_1 = parsed_1.get("nodes", [])
print(f"Latency: {duration_1:.2f} seconds")
print(f"JSON size: {len(cleaned_1)} characters")
print(f"Nodes found: {len(nodes_1)}")
print("Sample Node from Experiment 1:")
if nodes_1:
    print(json.dumps(nodes_1[0], indent=2))

# Setup Experiment 2 Prompt
EXP2_PROMPT = """You are a document understanding engine.
Return ONLY valid JSON.
Do not include markdown, code fences, comments, explanations, or any extra text.

Extract a document graph from the page image.

Required JSON schema:
{
  "nodes": [
    {
      "type": "heading|subheading|paragraph|table|list|equation|figure|caption|footer|header|reference|code|quote|form_field",
      "text": "...",
      "reading_order": 1,
      "semantic_category": "title|person|organization|address|date|identifier|heading|abstract|list_item|table|metadata|body_text|reference|footer",
      "entity_group": "...",
      "confidence": 1.0,
      "bbox": {
        "x1": 0,
        "y1": 0,
        "x2": 0,
        "y2": 0
      }
    }
  ]
}

Rules:
- Return normalized bounding boxes in the 0 to 1 range when possible.
- Use only the allowed node types and semantic categories.
- Preserve the visual reading order.
- Keep text verbatim where possible.
- For every text block assign a 'semantic_category' from the allowed list.
- For every text block assign an 'entity_group' id (blocks that belong to the same conceptual entity collection should share an entity_group id, e.g. inventor_1, inventor_2, applicant_1, applicant_2, address_1, address_2).
- Do NOT use document-specific labels.
- The response must be a single JSON object.
- Do NOT transcribe horizontal dividing lines, borders, or page separators.
"""

def call_exp2_gemini(image):
    pil_image = _ensure_pil_image(image)
    encoded_image = _pil_to_base64(pil_image)
    mime_type = "image/png"
    prompt = f"Page number: 1\nPipeline ID: exp2\n\n{EXP2_PROMPT}"
    
    body = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": prompt},
                    {"inline_data": {"mime_type": mime_type, "data": encoded_image}},
                ],
            }
        ],
        "generationConfig": {
            "temperature": 0.0,
            "topP": 0.95,
            "maxOutputTokens": 32768,
            "responseMimeType": "application/json",
            "thinkingConfig": {
                "thinkingBudget": 0
            }
        },
    }
    url = GEMINI_API_URL_TEMPLATE.format(model=GEMINI_MODEL_NAME, api_key=api_key)
    headers = {"Content-Type": "application/json"}
    
    for attempt in range(5):
        try:
            time.sleep(6.0)
            response = requests.post(url, headers=headers, json=body, timeout=300)
            if response.status_code >= 500 or response.status_code == 429:
                print(f"Temporary error {response.status_code}, retrying...")
                continue
            response.raise_for_status()
            rj = response.json()
            raw = _extract_gemini_text(rj)
            usage = rj.get("usageMetadata", {})
            return raw, usage
        except Exception as e:
            if attempt == 4:
                raise e
            print(f"Error on attempt {attempt}: {e}, retrying...")
            time.sleep(10.0)


print("\n=== Running Experiment 2: Additional Instructions ===")
t0 = time.perf_counter()
raw_text_2, usage_2 = call_exp2_gemini(img)
t1 = time.perf_counter()
duration_2 = t1 - t0
cleaned_2 = _clean_json_text(raw_text_2)
parsed_2 = json.loads(cleaned_2)

nodes_2 = parsed_2.get("nodes", [])
print(f"Latency: {duration_2:.2f} seconds")
print(f"JSON size: {len(cleaned_2)} characters")
print(f"Usage Stats: {usage_2}")
print(f"Nodes found: {len(nodes_2)}")
print("Sample Nodes from Experiment 2 (up to 20 nodes):")
dumped_nodes = []
for n in nodes_2[:20]:
    dumped_nodes.append({
        "node_id": n.get("reading_order"),
        "text": n.get("text")[:80] + "..." if n.get("text") else "",
        "type": n.get("type"),
        "semantic_category": n.get("semantic_category"),
        "entity_group": n.get("entity_group"),
        "confidence": n.get("confidence")
    })
print(json.dumps(dumped_nodes, indent=2))
