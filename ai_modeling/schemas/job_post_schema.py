from pydantic import BaseModel, Field
from typing import List, Optional, Dict

class JobPost(BaseModel):
    title: str = Field("", description="공고 제목")
    category: Optional[str] = Field(None, description="직종 / 카테고리")
    region: Optional[str] = Field(None, description="근무 지역 (구/시 등)")
    address: Optional[str] = Field(None, description="상세 주소")
    client: Optional[str] = Field(None, description="기관/클라이언트 명")
    schedule_days: List[str] = Field(default_factory=list, description="근무 요일 목록")
    time_slots: List[str] = Field(default_factory=list, description="시간대 (오전/오후/야간 등)")
    start_time: Optional[str] = Field(None, description="시작 시간 HH:MM:SS")
    end_time: Optional[str] = Field(None, description="종료 시간 HH:MM:SS")
    frequency: Optional[str] = Field(None, description="반복 주기 또는 횟수 (예: 하루 2번, 주 3회 등)")
    participants: Optional[int] = Field(None, description="모집 인원")
    wage_type: Optional[str] = Field(None, description="급여 형태: hourly/monthly/flat")
    hourly_wage: Optional[int] = Field(None, description="시급 (숫자)")
    wage_amount: Optional[str] = Field(None, description="그 외 급여 텍스트")
    qualifications: List[str] = Field(default_factory=list, description="지원 자격 요구사항")
    description: Optional[str] = Field(None, description="상세 설명")
    raw_text: str = Field("", description="원문 전체 텍스트")
    confidence: Dict[str, float] = Field(default_factory=dict, description="필드별 추출 신뢰도 (0~1)")

class JobPostResponse(BaseModel):
    success: bool
    post: JobPost
    message: Optional[str] = None
    session_id: Optional[str] = None
    needs_clarification: Optional[bool] = None
    missing_fields: Optional[List[str]] = None
    questions: Optional[List[str]] = None
    provider: Optional[str] = None
