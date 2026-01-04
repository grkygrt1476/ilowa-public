#ai_modeling/services/clova_ocr.py
import os
import json
import uuid
import time
import base64
import requests
from dotenv import load_dotenv

load_dotenv()

CLOVA_OCR_URL = os.getenv("CLOVA_OCR_URL")
CLOVA_OCR_SECRET = os.getenv("CLOVA_OCR_SECRET")

def clova_ocr_bytes_to_html(image_bytes: bytes):
    """
    CLOVA OCR 호출 후 image_data(dict)와 generated HTML(str)를 반환.
    환경변수가 없으면 간단한 mock을 반환 (개발용).
    """
    if not CLOVA_OCR_URL or not CLOVA_OCR_SECRET:
        # DEV fallback: return very small mock structure
        mock = {
            "image_data": {"fields": [], "tables": []},
            "html": "<html><body><p>OCR_KEY_NOT_SET</p></body></html>"
        }
        return mock

    img_base64 = base64.b64encode(image_bytes).decode("utf-8")
    payload = {
        "version": "V2",
        "requestId": str(uuid.uuid4()),
        "timestamp": int(round(time.time() * 1000)),
        "images": [
            {
                "name": "upload_image",
                "format": "png",
                "data": img_base64
            }
        ],
        "enableTableDetection": True
    }
    headers = {
        "Content-Type": "application/json",
        "X-OCR-SECRET": CLOVA_OCR_SECRET
    }
    resp = requests.post(CLOVA_OCR_URL, data=json.dumps(payload), headers=headers, timeout=30)
    resp.raise_for_status()
    result = resp.json()
    image_data = result.get("images", [])[0] if result.get("images") else {"fields": [], "tables": []}

    # Build HTML from fields + tables (similar to your earlier script)
    html_output = "<html><body>"
    html_output += "<div class='text-blocks'>"
    for field in image_data.get("fields", []):
        text = field.get("inferText", "")
        html_output += f"<p>{text}</p>"
    html_output += "</div>"

    tables = image_data.get("tables", [])
    for idx, table in enumerate(tables):
        html_output += f"<h3>Table {idx+1}</h3>"
        html_output += "<table border='1'>"
        if not table.get("cells"):
            continue
        max_row = max([c["rowIndex"] for c in table["cells"]]) + 1
        max_col = max([c["columnIndex"] for c in table["cells"]]) + 1
        grid = [["" for _ in range(max_col)] for _ in range(max_row)]
        for cell in table["cells"]:
            r = cell["rowIndex"]
            c = cell["columnIndex"]
            words = []
            for line in cell.get("cellTextLines", []):
                for w in line.get("cellWords", []):
                    words.append(w.get("inferText", ""))
            grid[r][c] = " ".join(words)
        for r in range(max_row):
            html_output += "<tr>"
            for c in range(max_col):
                html_output += f"<td>{grid[r][c]}</td>"
            html_output += "</tr>"
        html_output += "</table><br>"
    html_output += "</body></html>"

    return {"image_data": image_data, "html": html_output}


def run_clova_ocr(image_bytes: bytes):
    """
    Backwards-compatible wrapper used by routers that expects a simple
    function named `run_clova_ocr` which returns the generated HTML string.
    """
    result = clova_ocr_bytes_to_html(image_bytes)
    # If the underlying function returns our dict with 'html', return that.
    if isinstance(result, dict):
        return result.get("html", "")
    # Otherwise return whatever was returned (best-effort)
    return result
