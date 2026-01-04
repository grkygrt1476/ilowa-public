import time
import hashlib
import hmac
import base64
import os
import httpx # 동기/비동기 HTTP 클라이언트
from typing import Dict, Any

from backend_api.app.core.config import settings

def send_otp_sms(phone_number: str, code: str) -> bool:
    # 더미/로컬 모드면 외부 호출 생략
    if settings.USE_DUMMY_SMS or settings.ENVIRONMENT == "local":
        print(f"[SMS SIMULATION] To: {phone_number}, Code: {code}")
        return True

# ----------------------------------------------------
# 0. SENS 설정 정보 (환경 변수에서 로드)
# ----------------------------------------------------
# SECRET_KEY, ACCESS_KEY는 AWS Secrets Manager를 통해 안전하게 관리됩니다.
SENS_SECRET_KEY = os.environ.get("SENS_SECRET_KEY", "YOUR_SECRET_KEY_HERE")
SENS_ACCESS_KEY = os.environ.get("SENS_ACCESS_KEY", "YOUR_ACCESS_KEY_HERE")
SENS_SERVICE_ID = os.environ.get("SENS_SERVICE_ID", "YOUR_SERVICE_ID_HERE")
SENS_CALLING_NUMBER = os.environ.get("SENS_CALLING_NUMBER", "01012345678") # 등록된 발신 번호

SENS_API_URL = "https://sens.apigw.ntruss.com"
URI_PATH = f"/sms/v2/services/{SENS_SERVICE_ID}/messages"


# ====================================================
# 1. HMAC-SHA256 시그니처 생성 함수 (인증 핵심)
# ====================================================

def make_signature(method: str, uri: str, timestamp: str) -> str:
    """
    Naver SENS API 호출을 위한 x-ncp-apigw-signature-v2 헤더를 생성합니다.
    Secret Key를 사용하여 요청 내용을 HMAC-SHA256으로 암호화합니다.
    """
    # 1. 시그니처 대상 문자열 (Message String) 생성: SENS가 요구하는 포맷
    # 형식: METHOD + " " + URI + "\n" + TIMESTAMP + "\n" + ACCESS_KEY
    message_string = f"{method} {uri}\n{timestamp}\n{SENS_ACCESS_KEY}"
    
    # 2. Secret Key와 메시지를 UTF-8 바이트로 변환
    secret_key_bytes = bytes(SENS_SECRET_KEY, 'UTF-8')
    message_bytes = bytes(message_string, 'UTF-8')
    
    # 3. HMAC-SHA256 암호화
    signature_hash = hmac.new(secret_key_bytes, message_bytes, digestmod=hashlib.sha256).digest()
    
    # 4. Base64 인코딩 후 문자열로 반환
    signature = base64.b64encode(signature_hash).decode()
    return signature


# ====================================================
# 2. 동기 SMS 발송 클라이언트 함수 (요청에 따라 동기 방식으로 수정됨)
# ====================================================

def send_otp_sms(phone_number: str, otp_code: str):
    """
    httpx를 사용하여 OTP SMS를 동기적으로 발송합니다.
    """
    timestamp = str(int(time.time() * 1000)) # 타임스탬프 (밀리초 단위)
    method = "POST"

    # HMAC 시그니처 생성
    signature = make_signature(method, URI_PATH, timestamp)
    
    # HTTP 요청 헤더 설정
    headers = {
        'Content-Type': 'application/json; charset=utf-8',
        'x-ncp-apigw-timestamp': timestamp,
        'x-ncp-iam-access-key': SENS_ACCESS_KEY,
        'x-ncp-apigw-signature-v2': signature  # 생성된 HMAC 서명
    }
    
    # 요청 본문 (Body)
    body = {
        "type": "SMS",
        "contentType": "COMM", # 단문 메시지, 장문은 "LMS", 광고는 "AD"
        "countryCode": "82",
        "from": SENS_CALLING_NUMBER, # 등록된 발신 번호
        "content": f"[일로와] 인증번호: {otp_code} 입니다.",
        "messages": [
            {
                "to": phone_number,
                "content": f"[일로와] 인증번호: {otp_code} 입니다."
            }
        ]
    }

    # 동기 클라이언트 httpx.Client를 사용해 API 호출 / 실제 SENS API 호출 로직
    # with httpx.Client(base_url=SENS_API_URL, timeout=5.0) as client:
    #     # 동기 호출 client.post를 사용합니다.
    #     response = client.post(
    #         URI_PATH, 
    #         json=body, 
    #         headers=headers
    #     )
        
    # response.raise_for_status() # 4xx, 5xx 응답 시 예외 발생
    # return response.json()
    print(f"[OTP SIMULATION] SMS 발송 우회 성공. Code: {otp_code} (나중에 이 코드를 삭제하고 SENS API를 복구하세요)")
    return True # 무조건 True 반환