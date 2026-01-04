# from fastapi import APIRouter, HTTPException
# from typing import Dict, Any, List
# import uuid
# from services.clova_embedding import EmbeddingExecutor
# from schemas.job_post_schema import JobPost, JobPostResponse
# from routers.post_automation import append_to_csv

# router = APIRouter()

# # In-memory pending store: pending_id -> JobPost dict
# pending_posts: Dict[str, Dict[str, Any]] = {}
# _embedding = EmbeddingExecutor()

# DAY_INDEX = {
#     "월": 0, "월요일": 0,
#     "화": 1, "화요일": 1,
#     "수": 2, "수요일": 2,
#     "목": 3, "목요일": 3,
#     "금": 4, "금요일": 4,
#     "토": 5, "토요일": 5,
#     "일": 6, "일요일": 6,
# }


# def _days_to_mask(schedule_days: List[str]) -> str:
#     mask = ["0"] * 7
#     for d in schedule_days or []:
#         for key, idx in DAY_INDEX.items():
#             if key in d:
#                 mask[idx] = "1"
#                 break
#     return "".join(mask) if any(m == "1" for m in mask) else "1111111"


# def _compose_embedding_text(row: Dict[str, Any]) -> str:
#     parts = [
#         f"제목은 {row.get('title','')}입니다.",
#         f"참여자 수는 {row.get('participants','')}명입니다.",
#         f"시급은 {row.get('hourly_wage','')}원입니다.",
#         f"장소는 {row.get('place','')}입니다.",
#         f"주소는 {row.get('address','')}입니다.",
#         f"근무 요일은 {row.get('work_days','')}입니다.",
#         f"시작 시간은 {row.get('start_time','')}입니다.",
#         f"종료 시간은 {row.get('end_time','')}입니다.",
#         f"클라이언트는 {row.get('client','')}입니다.",
#         f"설명: {row.get('description','')}"
#     ]
#     return " ".join(parts)


# def _map_jobpost_to_csv_row(post: Dict[str, Any]) -> Dict[str, Any]:
#     # Map JobPost to CSV row fields expected by new_work_with_embeddings.csv
#     title = post.get("title") or ""
#     participants = post.get("participants") or 0
#     hourly_wage = post.get("hourly_wage") or 0
#     place = post.get("region") or ""
#     address = post.get("address") or ""
#     work_days = _days_to_mask(post.get("schedule_days") or [])
#     start_time = post.get("start_time") or "09:00:00"
#     end_time = post.get("end_time") or "18:00:00"
#     client = post.get("client") or "사용자 등록"
#     description = post.get("description") or post.get("raw_text") or ""

#     row = {
#         "title": title,
#         "participants": int(participants) if participants is not None else 0,
#         "hourly_wage": int(hourly_wage) if hourly_wage is not None else 0,
#         "place": place,
#         "address": address,
#         "work_days": work_days,
#         "start_time": start_time,
#         "end_time": end_time,
#         "client": client,
#         "description": description,
#     }

#     # Create embedding
#     emb_text = _compose_embedding_text(row)
#     row["embedding"] = _embedding.get_embedding(emb_text)
#     return row


# @router.post("/approval/submit")
# async def submit_for_approval(post: JobPost) -> Dict[str, Any]:
#     """Client submits a structured post for admin approval."""
#     pending_id = str(uuid.uuid4())
#     pending_posts[pending_id] = post.dict()
#     return {"success": True, "pending_id": pending_id}


# @router.get("/approval/pending")
# async def list_pending() -> Dict[str, Any]:
#     items = []
#     for pid, data in pending_posts.items():
#         items.append({"pending_id": pid, **data})
#     return {"success": True, "count": len(items), "items": items}


# @router.get("/approval/pending/{pending_id}")
# async def get_pending(pending_id: str) -> Dict[str, Any]:
#     if pending_id not in pending_posts:
#         raise HTTPException(status_code=404, detail="대기 중인 항목을 찾을 수 없습니다.")
#     return {"success": True, "item": pending_posts[pending_id]}


# @router.post("/approval/pending/{pending_id}/approve")
# async def approve_pending(pending_id: str) -> Dict[str, Any]:
#     if pending_id not in pending_posts:
#         raise HTTPException(status_code=404, detail="대기 중인 항목을 찾을 수 없습니다.")
#     post = pending_posts.pop(pending_id)

#     # Map and save to CSV
#     row = _map_jobpost_to_csv_row(post)
#     csv_path = "data/new_work_with_embeddings.csv"
#     append_to_csv(row, csv_path)

#     return {"success": True, "message": "승인되어 CSV에 저장되었습니다.", "saved": row}


# @router.post("/approval/pending/{pending_id}/reject")
# async def reject_pending(pending_id: str) -> Dict[str, Any]:
#     if pending_id not in pending_posts:
#         raise HTTPException(status_code=404, detail="대기 중인 항목을 찾을 수 없습니다.")
#     pending_posts.pop(pending_id)
#     return {"success": True, "message": "거절되어 삭제되었습니다."}
