from fastapi import HTTPException, status
from typing import Dict, Any

# 모든 사용자 정의 오류의 기본 클래스
class IlowaException(HTTPException):
    def __init__(self, status_code: int, detail: str, code: str, headers: Dict[str, Any] = None):
        super().__init__(status_code=status_code, detail=detail, headers=headers)
        self.code = code

# 인증 관련 오류 클래스
class AuthException(IlowaException):
    pass

class OTPException(AuthException):
    pass

class UserNotFoundException(AuthException):
    def __init__(self, detail: str = "사용자를 찾을 수 없습니다.", code: str = "USER_NOT_FOUND"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail, code=code)

class OTPCodeExpiredException(OTPException):
    def __init__(self, detail: str = "인증 코드가 만료되었습니다. 재전송해 주세요.", code: str = "CODE_EXPIRED"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail, code=code)

class OTPInvalidException(OTPException):
    def __init__(self, detail: str = "인증 코드가 일치하지 않거나 유효하지 않습니다.", code: str = "INVALID_CODE"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail, code=code)

class PINMismatchException(AuthException):
    def __init__(self, detail: str = "PIN이 일치하지 않습니다.", code: str = "PIN_MISMATCH"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail, code=code)

class PINLockedException(AuthException):
    def __init__(self, detail: str = "PIN 입력 오류 횟수 초과로 잠금되었습니다.", code: str = "PIN_LOCKED"):
        super().__init__(status_code=status.HTTP_423_LOCKED, detail=detail, code=code)

class RateLimitException(IlowaException):
    def __init__(self, detail: str = "잠시 후 다시 시도해 주세요.", code: str = "TOO_MANY_REQUESTS"):
        super().__init__(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=detail, code=code, headers={"Retry-After": "60"})
