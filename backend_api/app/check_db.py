import os
import sys

# ----------------------------------------------------
# Python 경로 설정: 프로젝트 루트를 sys.path에 추가
# ----------------------------------------------------
# 이 스크립트를 실행할 때, Python이 'backend_api' 폴더를 패키지 루트로 인식하게 합니다.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))


# 이제 절대 경로 대신 패키지 상대 경로로 임포트합니다.
from app.db.database import create_db_and_tables # 'backend_api' 대신 'app'부터 시작
from app.core.config import settings
from dotenv import load_dotenv

def test_db_connection():
    print("--- 1. 데이터베이스 연결 및 테이블 생성 시도 ---")
    try:
        # DB 연결 전에 .env 파일 로드
        # .env 파일이 backend_api 폴더에 있다고 가정하고 로드합니다.
        load_dotenv(dotenv_path='../.env') 
        
        # database.py에 정의된 함수를 호출합니다.
        create_db_and_tables()
        print("✅ 성공: 데이터베이스 연결이 확인되었으며 테이블이 생성되었습니다.")
        print("   PostgreSQL 콘솔에서 'ilowadb'를 확인해 보세요.")
    except Exception as e:
        # 실제 오류 메시지를 더 명확하게 출력합니다.
        print(f"❌ 실패: 데이터베이스 연결 중 치명적인 오류 발생.")
        print(f"   [오류 유형] {type(e).__name__}")
        print(f"   [오류 메시지] {e}")
        print("-" * 50)
        print("   [점검 사항] 1. PostgreSQL 서버가 실행 중인가요? 2. .env 파일의 ilowa_dev 비밀번호가 정확한가요?")

if __name__ == "__main__":
    test_db_connection()
