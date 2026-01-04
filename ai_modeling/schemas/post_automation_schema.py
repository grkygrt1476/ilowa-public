# # ai_modeling/schemas/post_automation_schema.py
# from pydantic import BaseModel
# from typing import Optional, List, Dict, Any

# class PostInput(BaseModel):
#     """
#     사용자가 업로드한 이미지 또는 텍스트 기반의 원본 공고 데이터
#     """
#     filename: str
#     content_type: str
#     size: int


# class ParsedJob(BaseModel):
#     """
#     OCR + HTML 파싱 후 구조화된 필드
#     """
#     raw_text: str
#     texts: List[str]
#     tables: List[List[List[str]]]

#     # optional 추출 필드
#     title: Optional[str] = None
#     participants: Optional[int] = None
#     hourly_wage: Optional[int] = None
#     place: Optional[str] = None
#     address: Optional[str] = None
#     work_days: Optional[str] = None
#     start_time: Optional[str] = None
#     end_time: Optional[str] = None
#     client: Optional[str] = None
#     description: Optional[str] = None


# class PostAutomationInput(BaseModel):
#     """
#     refine_with_clova_llm() 에 정제된 최종 필드를 전달하기 위한 모델
#     """
#     parsed_job: ParsedJob
#     need_refine: bool = True


# class RefinedJob(BaseModel):
#     """
#     최종 LLM까지 걸친 완전 정제 버전
#     """
#     title: str
#     participants: int
#     hourly_wage: int
#     place: str
#     address: str
#     work_days: str
#     start_time: str
#     end_time: str
#     client: str
#     description: str
#     summary: Optional[str] = None
