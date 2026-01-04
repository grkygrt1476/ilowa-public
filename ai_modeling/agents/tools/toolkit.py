#ai_mdeling/agents/tools/toolkit.py

"""
Tool Registry and Toolkit for ReAct Agent

다양한 추천 전략을 Tool로 구현하여 Agent가 상황에 따라 선택 가능하게 함
"""
import json
import math
from typing import Any, Callable, Dict, List, Optional

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from ai_modeling.agents.tools.csv_rag_tool import CSVRAGTool
from ai_modeling.services.providers import AIProvider, get_ai_provider


class ToolResult:
    """Tool 실행 결과를 표준화"""
    def __init__(self, success: bool, data: Any, message: str = ""):
        self.success = success
        self.data = data
        self.message = message
    
    def to_dict(self):
        return {
            "success": self.success,
            "data": self.data,
            "message": self.message
        }


class AgentToolkit:
    """
    Agent가 사용할 수 있는 모든 Tool 관리
    """
    
    def __init__(
        self,
        csv_path: Optional[str] = None,
        provider: Optional[AIProvider] = None,
    ):
        self.provider = provider or get_ai_provider()
        self.csv_tool = CSVRAGTool(csv_path, embedder=self.provider.embed_text)
        self.csv_path = str(self.csv_tool.csv_path)
        
        # Tool Registry
        self.tools: Dict[str, Callable] = {
            "rag_search": self.rag_search,
            "latest_jobs": self.latest_jobs,
            "profile_match_filter": self.profile_match_filter,
            "hybrid_search": self.hybrid_search,
            "region_specific_search": self.region_specific_search,
            "experience_based_search": self.experience_based_search,
            "price_filtered_search": self.price_filtered_search,
            "validate_recommendations": self.validate_recommendations,
        }
    
    # ==================== Tool 1: RAG Search ====================
    def rag_search(
        self,
        query: str,
        user_profile: Dict[str, Any] = None,
        top_k: int = 5,
        **kwargs
    ) -> ToolResult:
        """
        기본 RAG 검색 (embedding 기반 유사도)
        """
        try:
            if not query or not query.strip():
                return ToolResult(False, [], "빈 쿼리")
            
            print(f"[TOOL] RAG Search: {query}")
            
            # 프로필 정보 통합
            full_query = query
            if user_profile:
                profile_text = self._profile_to_text(user_profile)
                full_query += " | " + profile_text
            
            # CSV 검색
            results = self.csv_tool.query(full_query, top_k=top_k)
            
            # 추천 이유 추가
            results = self._add_recommendation_reason(results, user_profile)
            
            message = f"RAG 검색: {len(results)}개 결과"
            print(f"[TOOL] {message}")
            # If no results found, attempt safe fallbacks to guarantee some recommendations:
            # 1) Try region_specific_search if user regions are available
            # 2) Fall back to latest_jobs to return recent postings
            if len(results) == 0:
                fallback_results = []
                if user_profile and user_profile.get("regions"):
                    print("[TOOL] RAG 검색 결과 없음 -> 지역 기반 대체 검색 시도")
                    region_res = self.region_specific_search(user_profile.get("regions"), user_profile=user_profile, top_k=top_k)
                    if region_res.success and region_res.data:
                        fallback_results = region_res.data

                if not fallback_results:
                    print("[TOOL] 지역 기반 대체 결과 없음 -> 최신 공고로 대체")
                    latest_res = self.latest_jobs(user_profile=user_profile, top_k=top_k)
                    if latest_res.success and latest_res.data:
                        fallback_results = latest_res.data

                if fallback_results:
                    results = fallback_results
                    message = f"RAG 검색 결과 없음 — 대체 검색으로 {len(results)}개 반환"
                    print(f"[TOOL] {message}")

            return ToolResult(True, results, message)
        
        except Exception as e:
            error_msg = f"RAG 검색 실패: {str(e)}"
            print(f"[TOOL] {error_msg}")
            return ToolResult(False, [], error_msg)
    
    # ==================== Tool 2: Latest Jobs ====================
    def latest_jobs(
        self,
        user_profile: Dict[str, Any] = None,
        top_k: int = 5,
        **kwargs
    ) -> ToolResult:
        """
        최신순 공고들 (job_id 역순 = 최신순)
        """
        try:
            print(f"[TOOL] Latest Jobs")
            
            import pandas as pd
            df = pd.read_csv(self.csv_path)
            
            # 최신순 정렬
            df = df.sort_values('job_id', ascending=False).head(top_k)
            results = df.to_dict(orient='records')
            
            # embedding 제거
            for r in results:
                if 'embedding' in r:
                    del r['embedding']
            
            # 프로필 매칭 추가
            results = self._add_recommendation_reason(results, user_profile)
            
            message = f"최신 공고: {len(results)}개"
            print(f"[TOOL] {message}")
            
            return ToolResult(True, results, message)
        
        except Exception as e:
            error_msg = f"최신 공고 조회 실패: {str(e)}"
            print(f"[TOOL] {error_msg}")
            return ToolResult(False, [], error_msg)
    
    # ==================== Tool 3: Profile Match Filter ====================
    def profile_match_filter(
        self,
        recommendations: List[Dict],
        user_profile: Dict[str, Any],
        min_score: float = 0.5,
        **kwargs
    ) -> ToolResult:
        """
        기존 추천 결과를 프로필과 일치도 기준으로 필터링
        """
        try:
            print(f"[TOOL] Profile Match Filter (threshold: {min_score})")
            
            if not recommendations:
                return ToolResult(False, [], "필터링할 추천 결과가 없음")
            
            filtered = []
            for rec in recommendations:
                match_score = self._calculate_profile_match(rec, user_profile)
                if match_score >= min_score:
                    rec['profile_match_score'] = round(match_score * 100, 1)
                    filtered.append(rec)
            
            message = f"필터링 후: {len(filtered)}/{len(recommendations)}개 남음"
            print(f"[TOOL] {message}")
            
            return ToolResult(True, filtered, message)
        
        except Exception as e:
            error_msg = f"프로필 필터링 실패: {str(e)}"
            print(f"[TOOL] {error_msg}")
            return ToolResult(False, recommendations, error_msg)
    
    # ==================== Tool 4: Hybrid Search ====================
    def hybrid_search(
        self,
        query: str,
        user_profile: Dict[str, Any],
        top_k: int = 5,
        **kwargs
    ) -> ToolResult:
        """
        RAG + 프로필 필터링 결합 (하이브리드)
        """
        try:
            print(f"[TOOL] Hybrid Search")
            
            # 1단계: RAG 검색
            rag_result = self.rag_search(query, user_profile, top_k=top_k*2)
            if not rag_result.success:
                return rag_result
            
            # 2단계: 프로필 필터링
            filter_result = self.profile_match_filter(
                rag_result.data,
                user_profile,
                min_score=0.4
            )
            
            # 3단계: 점수 기반 재정렬
            results = filter_result.data if filter_result.success else rag_result.data
            results = sorted(
                results[:top_k],
                key=lambda x: x.get('match_score', 0),
                reverse=True
            )
            
            message = f"하이브리드 검색: {len(results)}개 결과"
            print(f"[TOOL] {message}")
            
            return ToolResult(True, results, message)
        
        except Exception as e:
            error_msg = f"하이브리드 검색 실패: {str(e)}"
            print(f"[TOOL] {error_msg}")
            return ToolResult(False, [], error_msg)
    
    # ==================== Tool 5: Region-Specific Search ====================
    def region_specific_search(
        self,
        regions: List[str],
        user_profile: Dict[str, Any] = None,
        top_k: int = 5,
        **kwargs
    ) -> ToolResult:
        """
        특정 지역 기반 검색 (정확한 필터링)
        """
        try:
            print(f"[TOOL] Region-Specific Search: {regions}")
            
            import pandas as pd
            df = pd.read_csv(self.csv_path)
            
            # 지역 필터링
            region_mask = df['place'].isin(regions) | df['address'].str.contains('|'.join(regions), case=False, na=False)
            filtered_df = df[region_mask].head(top_k)
            
            results = filtered_df.to_dict(orient='records')
            for r in results:
                if 'embedding' in r:
                    del r['embedding']
            
            results = self._add_recommendation_reason(results, user_profile)
            
            message = f"지역 검색: {len(results)}개 결과"
            print(f"[TOOL] {message}")
            
            return ToolResult(True, results, message)
        
        except Exception as e:
            error_msg = f"지역 검색 실패: {str(e)}"
            print(f"[TOOL] {error_msg}")
            return ToolResult(False, [], error_msg)
    
    # ==================== Tool 6: Experience-Based Search ====================
    def experience_based_search(
        self,
        experiences: List[str],
        user_profile: Dict[str, Any] = None,
        top_k: int = 5,
        **kwargs
    ) -> ToolResult:
        """
        경험 키워드 기반 검색
        """
        try:
            print(f"[TOOL] Experience-Based Search: {experiences}")
            
            import pandas as pd
            df = pd.read_csv(self.csv_path)
            
            # 경험 키워드 필터링
            exp_pattern = '|'.join(experiences)
            exp_mask = df['title'].str.contains(exp_pattern, case=False, na=False)
            filtered_df = df[exp_mask].head(top_k)
            
            results = filtered_df.to_dict(orient='records')
            for r in results:
                if 'embedding' in r:
                    del r['embedding']
            
            results = self._add_recommendation_reason(results, user_profile)
            
            message = f"경험 검색: {len(results)}개 결과"
            print(f"[TOOL] {message}")
            
            return ToolResult(True, results, message)
        
        except Exception as e:
            error_msg = f"경험 검색 실패: {str(e)}"
            print(f"[TOOL] {error_msg}")
            return ToolResult(False, [], error_msg)
    
    # ==================== Tool 7: Price-Filtered Search ====================
    def price_filtered_search(
        self,
        min_wage: int = 0,
        max_wage: int = 99999,
        query: str = "",
        user_profile: Dict[str, Any] = None,
        top_k: int = 5,
        **kwargs
    ) -> ToolResult:
        """
        시급 범위 필터링을 포함한 검색
        """
        try:
            print(f"[TOOL] Price-Filtered Search: {min_wage}~{max_wage}원")
            
            import pandas as pd
            df = pd.read_csv(self.csv_path)
            
            # 시급 필터링
            wage_mask = (df['hourly_wage'] >= min_wage) & (df['hourly_wage'] <= max_wage)
            filtered_df = df[wage_mask]
            
            # 추가로 쿼리가 있으면 적용
            if query and query.strip():
                # embedding 기반 검색은 비용이 높으므로, 간단히 제목/설명에서 찾기
                query_mask = (
                    filtered_df['title'].str.contains(query, case=False, na=False) |
                    filtered_df['description'].str.contains(query, case=False, na=False)
                )
                filtered_df = filtered_df[query_mask]
            
            results = filtered_df.head(top_k).to_dict(orient='records')
            for r in results:
                if 'embedding' in r:
                    del r['embedding']
            
            results = self._add_recommendation_reason(results, user_profile)
            
            message = f"시급 필터링: {len(results)}개 결과"
            print(f"[TOOL] {message}")
            
            return ToolResult(True, results, message)
        
        except Exception as e:
            error_msg = f"시급 필터링 실패: {str(e)}"
            print(f"[TOOL] {error_msg}")
            return ToolResult(False, [], error_msg)
    
    # ==================== Tool 8: Validate Recommendations ====================
    def validate_recommendations(
        self,
        recommendations: List[Dict],
        min_count: int = 3,
        min_avg_score: float = 0.5,
        **kwargs
    ) -> ToolResult:
        """
        추천 결과의 품질 검증
        """
        try:
            print(f"[TOOL] Validate Recommendations")
            
            if not recommendations:
                return ToolResult(False, [], "추천 결과가 없음")
            
            # 개수 확인
            count_ok = len(recommendations) >= min_count
            
            # 평균 점수 확인
            avg_score = np.mean([r.get('match_score', 50) for r in recommendations]) / 100
            score_ok = avg_score >= min_avg_score
            
            # 결과
            validation_report = {
                "total_count": len(recommendations),
                "count_ok": count_ok,
                "avg_score": round(avg_score, 2),
                "score_ok": score_ok,
                "is_valid": count_ok and score_ok
            }
            
            message = f"검증: {'통과' if validation_report['is_valid'] else '불통과'}"
            print(f"[TOOL] {message} - {len(recommendations)}개, 평균점수 {avg_score:.2f}")
            
            return ToolResult(True, validation_report, message)
        
        except Exception as e:
            error_msg = f"검증 실패: {str(e)}"
            print(f"[TOOL] {error_msg}")
            return ToolResult(False, {}, error_msg)
    
    # ==================== Helper Methods ====================
    
    def execute_tool(
        self,
        tool_name: str,
        **kwargs
    ) -> ToolResult:
        """
        Tool을 이름으로 실행
        """
        if tool_name not in self.tools:
            error_msg = f"알 수 없는 Tool: {tool_name}"
            print(f"[TOOL] {error_msg}")
            return ToolResult(False, [], error_msg)
        
        tool_func = self.tools[tool_name]
        return tool_func(**kwargs)
    
    def get_available_tools(self) -> Dict[str, str]:
        """
        사용 가능한 모든 Tool 목록과 설명
        """
        descriptions = {
            "rag_search": "Query embedding 기반 유사도 검색",
            "latest_jobs": "최신 등록된 공고들",
            "profile_match_filter": "프로필과 일치도 기반 필터링",
            "hybrid_search": "RAG + 프로필 필터링 결합",
            "region_specific_search": "지역 기반 정확한 검색",
            "experience_based_search": "경험 키워드 기반 검색",
            "price_filtered_search": "시급 범위 필터링 검색",
            "validate_recommendations": "추천 결과 품질 검증",
        }
        return descriptions
    
    def _profile_to_text(self, profile: Dict[str, Any]) -> str:
        """프로필을 자연어 텍스트로 변환"""
        text_parts = []
        
        if "regions" in profile:
            text_parts.append(f"지역: {', '.join(profile['regions'])}")
        if "days" in profile:
            text_parts.append(f"요일: {', '.join(profile['days'])}")
        if "time_slots" in profile:
            text_parts.append(f"시간대: {', '.join(profile['time_slots'])}")
        if "experiences" in profile:
            text_parts.append(f"경험: {', '.join(profile['experiences'])}")
        
        return " | ".join(text_parts)
    
    def _add_recommendation_reason(
        self,
        results: List[Dict],
        user_profile: Dict[str, Any] = None
    ) -> List[Dict]:
        """추천 이유 추가"""
        if not user_profile:
            return results
        
        for result in results:
            reason_parts = []
            
            # 지역 매칭
            if "regions" in user_profile:
                job_address = self._safe_text(result.get('address', ''))
                if any(region in job_address for region in user_profile["regions"]):
                    reason_parts.append("지역 일치")
            
            # 경험 매칭
            if "experiences" in user_profile:
                job_title = self._safe_text(result.get('title', ''))
                job_desc = self._safe_text(result.get('description', ''))
                if any(exp in job_title or exp in job_desc for exp in user_profile["experiences"]):
                    reason_parts.append("경험 일치")
            
            # 요일 매칭
            if "days" in user_profile:
                if self._match_days(result.get('work_days', ''), user_profile["days"]):
                    reason_parts.append("요일 일치")
            
            # 시간대 매칭
            if "time_slots" in user_profile:
                if self._match_time_slots(
                    result.get('start_time', ''),
                    result.get('end_time', ''),
                    user_profile["time_slots"]
                ):
                    reason_parts.append("시간대 일치")
            
            result['recommendation_reason'] = ', '.join(reason_parts) if reason_parts else "유사도 기반"
        
        return results
    
    def _calculate_profile_match(
        self,
        job: Dict,
        user_profile: Dict[str, Any]
    ) -> float:
        """
        공고와 프로필의 매칭도 계산 (0~1)
        """
        score = 0.5  # 기본 점수
        factors = 0
        
        # 지역 매칭
        if "regions" in user_profile:
            job_address = self._safe_text(job.get('address', ''))
            if any(region in job_address for region in user_profile["regions"]):
                score += 0.15
            factors += 1
        
        # 경험 매칭
        if "experiences" in user_profile:
            job_title = self._safe_text(job.get('title', ''))
            job_desc = self._safe_text(job.get('description', ''))
            if any(exp in job_title or exp in job_desc for exp in user_profile["experiences"]):
                score += 0.15
            factors += 1
        
        # 요일 매칭
        if "days" in user_profile:
            days_match = self._match_days(job.get('work_days', ''), user_profile["days"])
            if days_match:
                score += 0.15
            factors += 1
        
        # 시간대 매칭
        if "time_slots" in user_profile:
            time_match = self._match_time_slots(
                job.get('start_time', ''),
                job.get('end_time', ''),
                user_profile["time_slots"]
            )
            if time_match:
                score += 0.15
            factors += 1
        
        # 능력 매칭 (예: 체력, 들기 가능 무게 등)
        if "capabilities" in user_profile:
            cap_match = self._match_capabilities(job, user_profile["capabilities"])
            if cap_match:
                score += 0.1
            factors += 1
        
        # 시급 (있으면 좋음)
        if "preferred_wage" in user_profile:
            job_wage = job.get('hourly_wage', 0)
            if job_wage >= user_profile["preferred_wage"] * 0.8:
                score += 0.1
            factors += 1
        
        # 정규화
        if factors > 0:
            score = min(1.0, score)
        
        return score
    
    def _match_days(self, work_days_str: str, user_days: List[str]) -> bool:
        """
        요일 매칭 확인
        work_days_str: '1111111' 형태 (월화수목금토일, 1=가능, 0=불가)
        user_days: ["월요일 오전", "수요일 오전", ...] 형태
        """
        if work_days_str is None or not user_days:
            return False
        
        # work_days를 7자리 문자열로 변환 (부족하면 0으로 채움)
        work_days_str = self._safe_text(work_days_str).strip()
        if not work_days_str:
            return False
        if len(work_days_str) < 7:
            work_days_str = work_days_str.ljust(7, '0')
        
        # 요일 매핑 (월=0, 화=1, ..., 일=6)
        day_mapping = {
            "월": 0, "화": 1, "수": 2, "목": 3, "금": 4, "토": 5, "일": 6,
            "월요일": 0, "화요일": 1, "수요일": 2, "목요일": 3,
            "금요일": 4, "토요일": 5, "일요일": 6
        }
        
        # 사용자가 원하는 요일 확인
        for user_day in user_days:
            # "월요일 오전" → "월요일" 추출
            day_name = user_day.split()[0] if user_day else ""
            
            # 매핑에서 인덱스 찾기
            day_index = None
            for key, idx in day_mapping.items():
                if key in day_name:
                    day_index = idx
                    break
            
            if day_index is not None and day_index < len(work_days_str):
                # work_days에서 해당 요일이 1(가능)인지 확인
                if work_days_str[day_index] == '1':
                    return True
        
        return False
    
    def _match_time_slots(self, start_time: str, end_time: str, user_time_slots: List[str]) -> bool:
        """
        시간대 매칭 확인
        start_time: "9:00:00" 형태
        end_time: "18:00:00" 형태
        user_time_slots: ["오전", "오후"] 형태
        """
        if not start_time or not end_time or not user_time_slots:
            return False
        
        try:
            # 시간 파싱 (HH:MM:SS → HH)
            start_hour = int(self._safe_text(start_time).split(':')[0])
            end_hour = int(self._safe_text(end_time).split(':')[0])
            
            for time_slot in user_time_slots:
                slot_lower = time_slot.lower()
                
                # 오전: 6~12시
                if "오전" in slot_lower:
                    # 근무시간이 오전 시간대와 겹치는지 확인
                    if start_hour < 12 and end_hour > 6:
                        return True
                
                # 오후: 12~18시
                elif "오후" in slot_lower:
                    if start_hour < 18 and end_hour > 12:
                        return True
                
                # 저녁: 18~24시
                elif "저녁" in slot_lower or "야간" in slot_lower:
                    if start_hour < 24 and end_hour > 18:
                        return True
            
            return False
        
        except:
            return False
    
    def _match_capabilities(self, job: Dict, user_capabilities: Dict[str, Any]) -> bool:
        """
        능력 매칭 확인
        user_capabilities: {"can_lift": 10} 형태 (10kg까지 들 수 있음)
        """
        if not user_capabilities:
            return True  # 능력 정보가 없으면 통과
        
        # 체력/들기 요구사항 체크
        if "can_lift" in user_capabilities:
            # job description에서 무게 요구사항 추출 (간단한 휴리스틱)
            job_desc = self._safe_text(job.get('description', '')).lower()
            
            # 무거운 작업 키워드가 있으면 체크
            heavy_keywords = ["무거운", "중량", "운반", "적재", "하역"]
            if any(keyword in job_desc for keyword in heavy_keywords):
                # 사용자가 10kg 이상 들 수 있으면 OK
                if user_capabilities["can_lift"] >= 10:
                    return True
                else:
                    return False
        
        return True  # 특별한 요구사항이 없으면 통과

    def _safe_text(self, value: Any) -> str:
        """Ensure any field pulled from CSV is safely converted to string."""
        if value is None:
            return ""
        try:
            if isinstance(value, float) and math.isnan(value):
                return ""
        except Exception:
            pass
        return str(value)
