# from fastapi import APIRouter, UploadFile, File, HTTPException
# from services.clova_ocr import run_clova_ocr
# from services.html_parser import parse_html_to_structured
# from services.clova_llm import refine_with_clova_llm
# from services.clova_embedding import EmbeddingExecutor
# from agents.posting_agent import PostingAutomationAgent
# from utils.db import save_sql_file
# import traceback
# import os
# import csv
# import json

# router = APIRouter()
# embedding_executor = EmbeddingExecutor()  # Embedding 생성 객체
# posting_agent = PostingAutomationAgent()


# def append_to_csv(row: dict, path: str):
#     """
#     CSV 마지막 행 다음 줄에 새 행 append
#     - embedding은 JSON 배열 형태 그대로 저장
#     - job_id 자동 증가
#     """
#     #row_copy = row.copy()
#     row_copy={}
#     for key, value in row.items():
#         row_copy[key]=value

#     # embedding JSON 배열로 변환
# #    if "embedding" in row_copy:
# #        row_copy["embedding"] = json.dumps(row_copy["embedding"], ensure_ascii=False)

# # embedding 리스트만 숫자 배열로 변환
#     if "embedding" in row_copy and isinstance(row_copy["embedding"], list):
#         row_copy["embedding"] = "[" + ", ".join(str(x) for x in row_copy["embedding"]) + "]"


#     # job_id 자동 증가
#     last_id = 0
#     if os.path.isfile(path):
#         with open(path, "r", encoding="utf-8-sig", newline="") as f:
#             reader = csv.DictReader(f)
#             rows = list(reader)
#             if rows and "job_id" in rows[0]:
#                 last_id = int(rows[-1]["job_id"])
#     row_copy["job_id"] = last_id + 1

#     # CSV 컬럼 순서 고정
#     field_order = [
#         "job_id", "title", "participants", "hourly_wage", "place", "address",
#         "work_days", "start_time", "end_time", "client", "description", "embedding"
#     ]

#     # CSV append
#     file_exists = os.path.isfile(path)
#     with open(path, "a", encoding="utf-8-sig", newline="\n") as f:
#         writer = csv.DictWriter(f, fieldnames=field_order)
#         if not file_exists:
#             writer.writeheader()
#         # 필드 순서에 맞춰 dict 생성
#         row_to_write = {k: row_copy.get(k, "") for k in field_order}
#         writer.writerow(row_to_write)

# @router.post("/extract")
# async def extract_job_post(file: UploadFile = File(...), save_artifacts: bool = True):
#     """
#     이미지 파일 업로드 → OCR → HTML → 파싱 → CLOVA LLM 정제 → embedding 생성 → CSV/SQL 저장
#     """
#     try:
#         image_bytes = await file.read()

#         # 이미지 → PostingAutomationAgent로 구조화(LLM 생성 포함)
#         result = posting_agent.extract_from_image_bytes(image_bytes)
#         if not result.get("success"):
#             raise HTTPException(status_code=400, detail=result.get("message", "추출 실패"))

#         job = result.get("post", {})

#         # JobPost → CSV row 매핑
#         DAY_INDEX = {
#             "월": 0, "월요일": 0,
#             "화": 1, "화요일": 1,
#             "수": 2, "수요일": 2,
#             "목": 3, "목요일": 3,
#             "금": 4, "금요일": 4,
#             "토": 5, "토요일": 5,
#             "일": 6, "일요일": 6,
#         }

#         def days_to_mask(schedule_days):
#             mask = ["0"] * 7
#             for d in schedule_days or []:
#                 for key, idx in DAY_INDEX.items():
#                     if key in d:
#                         mask[idx] = "1"
#                         break
#             return "".join(mask) if any(m == "1" for m in mask) else "1111111"

#         row = {
#             "title": job.get("title") or "",
#             "participants": int(job.get("participants") or 1),
#             "hourly_wage": int(job.get("hourly_wage") or 0),
#             "place": job.get("region") or "",
#             "address": job.get("address") or "",
#             "work_days": days_to_mask(job.get("schedule_days") or []),
#             "start_time": job.get("start_time") or "09:00:00",
#             "end_time": job.get("end_time") or "18:00:00",
#             "client": job.get("client") or "사용자 등록",
#             "description": job.get("description") or job.get("raw_text") or "",
#         }

#         # Embedding 생성
#         text_for_embedding = " ".join([
#             f"제목은 {row.get('title','')}입니다.",
#             f"참여자 수는 {row.get('participants','')}명입니다.",
#             f"시급은 {row.get('hourly_wage','')}원입니다.",
#             f"장소는 {row.get('place','')}입니다.",
#             f"주소는 {row.get('address','')}입니다.",
#             f"근무 요일은 {row.get('work_days','')}입니다.",
#             f"시작 시간은 {row.get('start_time','')}입니다.",
#             f"종료 시간은 {row.get('end_time','')}입니다.",
#             f"클라이언트는 {row.get('client','')}입니다.",
#             f"설명: {row.get('description','')}"
#         ])
#         embedding_vector = embedding_executor.get_embedding(text_for_embedding)
#         row["embedding"] = embedding_vector

#         # CSV/SQL 저장
#         if save_artifacts:
#             csv_path = "data/new_work_with_embeddings.csv"
#             append_to_csv(row, csv_path)

#             sql_path = "data/insert_job.sql"
#             refined_sql = row.copy()
#             refined_sql["embedding"] = json.dumps(refined_sql["embedding"], ensure_ascii=False)
#             save_sql_file(refined_sql, sql_path)

#         # 생성된 JobPost와 저장된 Row를 함께 반환
#         return {"status": "success", "post": job, "saved_row": row}

#     except Exception as e:
#         traceback.print_exc()
#         raise HTTPException(status_code=500, detail=str(e))
    