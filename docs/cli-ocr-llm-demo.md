CLI Screenshot Recipe: Schema-less LLM Call (OCR Parsing)

목적
- 스키마 없이 LLM을 호출했을 때 JSON이 제멋대로 나오는 장면을 CLI에서 재현해 스샷으로 남긴다.
- 샘플 이미지: ai_modeling/sample/test_post.png (Clova OCR 사용 가정)
- 이 출력은 자기소개서 4-③의 "초기 실패" 캡처로 사용.

빠른 사용법
1) 터미널에서 아래 실행 (네트워크 호출 없음, 출력만 생성):
   ````bash
   python ai_modeling/scripts/llm_prompt_demo.py
   ````
2) 출력 화면을 그대로 캡처: 상단의 이미지 경로/사이즈, 가운데 프롬프트 원문, 하단의 AI 첫 응답 JSON이 모두 보이게 세로로 길게 찍는다.
3) 필요하면 --ocr-text로 다른 OCR 결과 문장을 넣어 재촬영: 
   ````bash
   python ai_modeling/scripts/llm_prompt_demo.py --ocr-text "주중 10~16시, 시급 1.5만, 강남구 모니터링"
   ````
4) 실제 Clova LLM 호출까지 찍고 싶다면 (CLOVA_LLM_URL/CLOVA_LLM_API_KEY가 .env에 있을 때):
   ````bash
   python ai_modeling/scripts/llm_prompt_demo.py --live
   ````
   - 응답이 내려오면 "Live Clova call (raw JSON response)" 섹션에 API 결과가 그대로 출력됨.

출력 구성(예시)
- Prompt: "다음 전단지 OCR 텍스트를 공고 정보 JSON으로 뽑아줘..." (스키마 지시 없음)
- AI Reply: days가 문자열, time이 문자열, hourly_wage가 문자열, address/benefits가 할루시네이션으로 채워짐

스크린샷 팁
- 커서가 남아 있는 터미널 창을 그대로 찍어 "방금 실행" 느낌을 준다.
- 명령어와 출력 상단/하단이 모두 보이도록 세로 길이 확보.
- 추가 컷이 필요하면 --ocr-text로 다른 문장을 넣어 2회 실행 후 위아래로 이어서 캡처.

주의사항 (놓치지 말 것)
- 프롬프트/응답 텍스트를 수정하지 않는다. 오타나 잘못된 값도 그대로 캡처.
- API 키나 민감 정보는 화면에 노출되지 않도록 한다(이 스크립트는 네트워크 호출 없음).
- 실제 Clova OCR을 돌릴 경우, OCR 원문도 같이 기록해두면 이후 개선 근거로 쓰기 좋다.
- "왜 잘못인지" 설명은 캡처 밖에서 별도 텍스트로 붙이고, JSON 본문은 가리지 않는다.

LLM과 진행 상황 공유 방법
- 같은 세션에서 "이 응답이 스키마를 어긴 이유를 설명해"라고 묻고 답을 받아 추가 컷으로 캡처하면 개선 타이밍 설명이 수월하다.
- 프롬프트를 조정할 때마다 이유를 한 줄로 메모(예: "benefits를 허위로 생성해 키 제약 강화") 후 다음 호출 화면과 함께 제출.
