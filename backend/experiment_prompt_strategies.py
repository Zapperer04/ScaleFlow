import os
import sys
import json
import time
import requests

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from services.document_preprocessor import DocumentPreprocessor, _get_gemini_api_key, GEMINI_MODEL_NAME, GEMINI_API_URL_TEMPLATE, _pil_to_base64, _ensure_pil_image, _clean_json_text, _extract_gemini_text

pdf_path = r"storage/uploads/178_PBL_Patent.pdf"
dp = DocumentPreprocessor(pdf_path)
images = dp.render_document(max_pages=1, dpi=300)
img = images[0]
api_key = _get_gemini_api_key()

STRATEGY_1_PROMPT = """You are a document understanding engine.
Extract a document graph. Return ONLY JSON.
Required JSON schema:
{
  "nodes": [
    {
      "structural_type": "paragraph|heading|header|footer|list_item|table_cell",
      "text": "...",
      "reading_order": 1,
      "semantic_category": "person|organization|identifier|date|location|title|heading|metadata|body_text",
      "entity_group": "entity_group_001",
      "bbox": {"x1": 0.0, "y1": 0.0, "x2": 1.0, "y2": 1.0}
    }
  ]
}
Rule: Assign a unique entity_group to each logical real-world entity. All attributes belonging to the same entity (e.g. name, address, affiliation) must share the same entity_group.
"""

STRATEGY_2_PROMPT = """You are a document understanding engine.
Extract a document graph. Return ONLY JSON.
Required JSON schema:
{
  "nodes": [
    {
      "structural_type": "paragraph|heading|header|footer|list_item|table_cell",
      "text": "...",
      "reading_order": 1,
      "semantic_category": "person|organization|identifier|date|location|title|heading|metadata|body_text",
      "entity_group": "entity_group_001",
      "bbox": {"x1": 0.0, "y1": 0.0, "x2": 1.0, "y2": 1.0}
    }
  ]
}
Rule: First identify conceptual entities. Then attach all semantically related blocks (e.g. adjacent names, titles, addresses, locations) to the same entity_group. Prefer under-segmentation (grouping related details together) over over-segmentation.
"""

def call_gemini(prompt):
    pil_image = _ensure_pil_image(img)
    encoded_image = _pil_to_base64(pil_image)
    mime_type = "image/png"
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
            "thinkingConfig": {"thinkingBudget": 0}
        },
    }
    url = GEMINI_API_URL_TEMPLATE.format(model=GEMINI_MODEL_NAME, api_key=api_key)
    headers = {"Content-Type": "application/json"}
    
    for attempt in range(5):
        try:
            time.sleep(10.0 + attempt * 5)
            response = requests.post(url, headers=headers, json=body, timeout=300)
            if response.status_code >= 500 or response.status_code == 429:
                print(f"Server error {response.status_code}, retrying...")
                continue
            response.raise_for_status()
            rj = response.json()
            raw = _extract_gemini_text(rj)
            return json.loads(_clean_json_text(raw))
        except Exception as e:
            if attempt == 4:
                raise e
            print(f"Error on attempt {attempt}: {e}, retrying...")
            time.sleep(15.0)


print("=== Running Strategy 1 ===")
res_1 = call_gemini(STRATEGY_1_PROMPT)
nodes_1 = res_1.get("nodes", [])
groups_1 = [n.get("entity_group") for n in nodes_1 if n.get("entity_group")]
print("Strategy 1 unique groups count:", len(set(groups_1)))
print("Strategy 1 sample grouped node:", nodes_1[7] if len(nodes_1) > 7 else "")

print("\n=== Running Strategy 2 ===")
res_2 = call_gemini(STRATEGY_2_PROMPT)
nodes_2 = res_2.get("nodes", [])
groups_2 = [n.get("entity_group") for n in nodes_2 if n.get("entity_group")]
print("Strategy 2 unique groups count:", len(set(groups_2)))
print("Strategy 2 sample grouped node:", nodes_2[7] if len(nodes_2) > 7 else "")
