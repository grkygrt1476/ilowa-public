from bs4 import BeautifulSoup
from typing import Dict, Any
import re

def clean_text(text: str) -> str:
    if not text:
        return ""
    text = text.replace("\n", " ").replace("\t", " ").strip()
    text = " ".join(text.split())
    return text

def parse_html_to_structured(html: str) -> Dict[str, Any]:
    """
    BeautifulSoup로 HTML을 파싱하여 구조화 dict 반환
    - raw_text 포함
    """
    soup = BeautifulSoup(html, "html.parser")
    result = {"raw_text": soup.get_text(separator="\n")}

    # 텍스트 블록
    p_list = [clean_text(p.text) for p in soup.find_all("p") if clean_text(p.text)]
    result["texts"] = p_list

    # 테이블
    tables = []
    for table in soup.find_all("table"):
        rows = []
        trs = table.find_all("tr")
        for tr in trs:
            cols = [clean_text(td.text) for td in tr.find_all("td")]
            if cols:
                rows.append(cols)
        tables.append(rows)
    result["tables"] = tables

    # 기본 추출 (two-table layout)
    try:
        if len(tables) >= 1:
            t1 = tables[0]
            if len(t1) > 0 and len(t1[0]) > 1:
                result["title"] = clean_text(t1[0][1])
            if len(t1) > 1 and len(t1[1]) > 1:
                m = re.search(r"(\d+)", t1[1][1])
                result["participants"] = int(m.group(1)) if m else 0
            if len(t1) > 1 and len(t1[1]) > 4:
                m = re.sub(r"[^0-9]", "", t1[1][4])
                monthly = int(m) if m else 0
                result["monthly_wage"] = monthly
                result["hourly_wage"] = round(monthly / 60) if monthly else 0
            if len(t1) > 4 and len(t1[4]) > 1:
                result["address"] = clean_text(t1[4][1])
            # client
            client = ""
            for row in t1:
                for i, cell in enumerate(row):
                    if "모집기관" in cell:
                        if i+1 < len(row):
                            client = row[i+1]
                        break
                if client:
                    break
            result["client"] = client or "미상"
        # description from second table
        if len(tables) > 1:
            t2 = tables[1]
            desc_lines = []
            for row in t2[3:]:
                if row:
                    desc_lines.append(row[-1])
            result["description"] = ", ".join([d for d in desc_lines if d])
    except Exception:
        pass

    return result
