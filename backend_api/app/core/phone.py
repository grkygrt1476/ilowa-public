# app/core/phone.py
import re
def to_e164_kr(raw:str|None)->str|None:
    if not raw: return None
    digits = re.sub(r"\D","", raw)
    if digits.startswith("82"):
        return f"+{digits}"
    if digits.startswith("010") and len(digits)==11:
        return f"+82{digits[1:]}"
    if raw.startswith("+"):
        return raw
    return None
