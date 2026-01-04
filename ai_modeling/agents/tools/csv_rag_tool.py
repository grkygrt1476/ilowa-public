# agents/tools/csv_rag_tool.py
import json
from pathlib import Path
from typing import Callable, List, Optional

import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity

from ai_modeling.utils.rag_paths import resolve_rag_csv_path

EMBEDDING_COLUMN_CANDIDATES = ("embedding", "embeddings", "vector", "embedding_vector")


class CSVRAGTool:
    def __init__(
        self,
        csv_path: Optional[str] = None,
        embedder: Optional[Callable[[str], List[float]]] = None,
    ):
        self._embedder = embedder
        self.csv_path = Path(csv_path) if csv_path else resolve_rag_csv_path()
        if self.csv_path.suffix.lower() != ".csv":
            raise ValueError(f"RAG input must be CSV (+embedding). Got: {self.csv_path}")

        self.df = pd.read_csv(self.csv_path, dtype={"job_id": int})
        self.embedding_column = self._find_embedding_column()
        self.embedding_dim = None
        self._prepare_embeddings()

    def _find_embedding_column(self) -> str:
        columns = list(self.df.columns)
        for name in EMBEDDING_COLUMN_CANDIDATES:
            if name in columns:
                return name
        for col in columns:
            if "embedding" in col.lower():
                return col
        raise ValueError(f"Embedding column not found in CSV: {self.csv_path}")

    def _prepare_embeddings(self) -> None:
        def _to_np(x):
            if pd.isna(x):
                return None
            if isinstance(x, str):
                try:
                    arr = json.loads(x)
                except Exception:
                    try:
                        arr = eval(x)
                    except Exception:
                        return None
                arr_np = np.array(arr, dtype=float)
                if self.embedding_dim is None:
                    self.embedding_dim = len(arr_np)
                    print(f"[INFO] CSV Embedding 차원: {self.embedding_dim}")
                return arr_np
            if isinstance(x, (list, tuple, np.ndarray)):
                arr_np = np.array(x, dtype=float)
                if self.embedding_dim is None:
                    self.embedding_dim = len(arr_np)
                    print(f"[INFO] CSV Embedding 차원: {self.embedding_dim}")
                return arr_np
            return None

        self.df[self.embedding_column] = self.df[self.embedding_column].apply(_to_np)

        if self.embedding_dim is None:
            self.embedding_dim = 1024
            print(f"[WARN] Embedding 차원을 결정할 수 없어 기본값 {self.embedding_dim} 사용")

        self.df[self.embedding_column] = self.df[self.embedding_column].apply(
            lambda x: np.zeros(self.embedding_dim) if x is None else x
        )

    def query(self, user_query, top_k=5):
        """
        사용자 쿼리로 유사도 검색
        """
        if not user_query or str(user_query).strip() == "":
            print("[WARN] 빈 쿼리")
            return []

        print(f"[INFO] 검색 쿼리: {user_query}")

        try:
            if not self._embedder:
                raise RuntimeError("Embedding 함수가 설정되지 않았습니다.")
            query_emb = self._embedder(user_query)
            if not query_emb:
                print("[ERROR] Query embedding 생성 실패 (빈 결과)")
                return []

            query_emb = np.array(query_emb, dtype=float)
            print(f"[INFO] Query embedding 차원: {len(query_emb)}")

            if len(query_emb) != self.embedding_dim:
                print(f"[ERROR] 차원 불일치! Query: {len(query_emb)}, CSV: {self.embedding_dim}")
                return []

        except Exception as e:
            print(f"[ERROR] Embedding 생성 실패: {e}")
            return []

        def score_fn(x):
            try:
                sim = float(cosine_similarity([query_emb], [x])[0][0])
                return sim
            except Exception as e:
                print(f"[ERROR] Similarity 계산 실패: {e}")
                return 0.0

        self.df["score"] = self.df[self.embedding_column].apply(score_fn)

        print(
            f"[INFO] Score 통계: min={self.df['score'].min():.4f}, "
            f"max={self.df['score'].max():.4f}, mean={self.df['score'].mean():.4f}"
        )

        top = self.df.sort_values("score", ascending=False).head(top_k)
        results = top.to_dict(orient="records")

        cleaned_results = []
        for r in results:
            if isinstance(r, dict):
                item = dict(r)
                item.pop(self.embedding_column, None)
                cleaned_results.append(item)
            else:
                cleaned_results.append(r)

        print(f"[INFO] 추천 결과 {len(cleaned_results)}개 반환")
        return cleaned_results
