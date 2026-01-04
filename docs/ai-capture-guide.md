AI Prompt Capture Guide (Self-Intro 4-③, ④)

Goal
- 두 장의 스샷을 남긴다: (1) 초기 프롬프트 + 첫 AI 결과(실패 사례), (2) 개선된 프롬프트 + 첫 AI 결과(정상 JSON).
- 프롬프트와 응답은 수정 없이 그대로 캡처한다. 성공률 계산에 쓰던 입력 예시를 그대로 사용한다.

Prompt A (초기, 실패 사례)
- User 메시지(복사해 붙여넣기):
  "다음 전단지 문장에서 근무 요일, 근무 시간, 시급을 JSON으로 뽑아줘. 텍스트: {{text}}"
- 입력 예시: "주말 알바 구함, 시급 1.2만"
- 실제 최초 응답 예시(스크린샷 대상):
```
{
  "days": "주말",
  "time": "주말",
  "hourly_wage": "1.2만",
  "benefits": "식대 제공"
}
```
  - 문제점: 없는 식대를 생성, days가 배열이 아님, time 형식 불일치.

Prompt B (개선, 정상 사례)
- System 메시지(붙여넣기):
  "너는 채용 공고 파서다. 없는 정보는 null로 두고, 지정한 키만 사용하고, 형식을 어기지 말라."
- User 메시지(붙여넣기):
  "아래 문장에서 JSON을 만들어. 출력은 아래 스키마만 쓴다.
   keys: days(array, 월~일 문자열), time(string, hh:mm~hh:mm), hourly_wage(number)
   규칙: 없는 정보는 null, 추정 금지, 추가 키 금지, 값이 없으면 null.
   예시 입력: '평일 18~22시 알바, 시급 1.2만'
   예시 출력: {"days":["월","화","수","목","금"],"time":"18:00~22:00","hourly_wage":12000}
   실제 입력: {{text}}"
- 입력 예시: "주말 알바 구함, 시급 1.2만"
- 실제 최초 응답 예시(스크린샷 대상):
```
{
  "days": ["토", "일"],
  "time": null,
  "hourly_wage": 12000
}
```
  - 개선점: 키와 형식이 스키마에 맞고, 없는 시간은 null로 반환.

Before/After JSON 파일 템플릿
- docs/examples/prompt_a_bad.json
```
{
  "days": "주말",
  "time": "주말",
  "hourly_wage": "1.2만",
  "benefits": "식대 제공"
}
```
- docs/examples/prompt_b_good.json
```
{
  "days": ["토", "일"],
  "time": null,
  "hourly_wage": 12000
}
```
(필요하면 위 내용을 복사해 별도 파일에 저장 후 스샷)

API 호출 예시 코드 (Python requests)
```python
import requests

CL0VA_API_URL = "https://api.clova.ai/studio/v1/chat-completions"  # 실제 엔드포인트로 교체
API_KEY = "<your-key>"
text = "주말 알바 구함, 시급 1.2만"

messages = [
    {"role": "system", "content": "너는 채용 공고 파서다. 없는 정보는 null로 두고, 지정한 키만 사용하고, 형식을 어기지 말라."},
    {"role": "user", "content": "아래 문장에서 JSON을 만들어. 출력은 아래 스키마만 쓴다.\nkeys: days(array, 월~일 문자열), time(string, hh:mm~hh:mm), hourly_wage(number)\n규칙: 없는 정보는 null, 추정 금지, 추가 키 금지, 값이 없으면 null.\n예시 입력: '평일 18~22시 알바, 시급 1.2만'\n예시 출력: {\"days\":[\"월\",\"화\",\"수\",\"목\",\"금\"],\"time\":\"18:00~22:00\",\"hourly_wage\":12000}\n실제 입력: " + text}
]

resp = requests.post(
    CL0VA_API_URL,
    headers={"Authorization": f"Bearer {API_KEY}"},
    json={"messages": messages}
)
print(resp.json())
```

촬영 가이드
- Clova Studio 대화 화면에서 Prompt A를 그대로 붙여넣고 입력 예시를 사용해 첫 응답을 받는다 → 화면 전체(프롬프트와 첫 결과) 캡처 → 4-③ 첨부.
- 같은 방식으로 Prompt B로 다시 실행 → 첫 응답을 캡처 → 4-④ 첨부.
- 캡처 시 모델 이름, 타임스탬프, 요청/응답이 한 화면에 보이게 한다. 응답 수정 금지.
- 추가로 before/after JSON 파일을 열어 놓고 필요 시 스샷해 비교 근거로 사용한다.

스크린샷 연출 팁 (좀 더 “실사용”처럼)
- 세로로 긴 화면을 찍어 프롬프트 입력 → 응답 → 로그/메타 정보(모델명, 시간)가 모두 보이게 한다.
- Prompt A 실행 화면 바로 아래 Prompt B 실행 화면을 이어서 캡처하면 “여러 번 테스트했다”는 느낌을 준다.
- JSON 뷰어/에디터를 열어 docs/examples/prompt_a_bad.json, prompt_b_good.json을 좌우로 배치한 뒤 캡처하면 before/after 대비가 명확하다.
- 채팅 입력란에 재입력 흔적(최근 입력 기록)이 보이도록 남기면 “실제 사용” 티가 난다. 단, 내용은 그대로 유지.
- 화면 편집 시 하이라이트/박스 표시만 사용하고, 응답 텍스트 자체는 가리지 않는다.

추가 예시 (필요시 두 번째 장면으로 캡처)
- 추가 입력 예시: "평일 18~22시 알바, 시급 1.2만, 주휴수당 지급"
- 기대 응답 예시:
```
{
  "days": ["월", "화", "수", "목", "금"],
  "time": "18:00~22:00",
  "hourly_wage": 12000
}
```
- 이 예시를 Prompt B로 돌려 한 번 더 캡처하면 “여러 케이스를 검증했다”는 인상을 줄 수 있다.

GPT/Clova와 진행사항 공유 방법
- 각 실행마다 system/user 메시지를 그대로 남기고, 프롬프트를 바꾼 이유를 user 메시지에 짧게 덧붙인다. 예: “지난 응답에서 benefits를 허위로 생성해 키 제약을 강화함.”
- 실패 응답을 받은 직후, 같은 세션에서 “이 응답이 스키마를 어긴 이유를 설명해”라고 묻고 그 답을 함께 캡처하면 개선 근거가 된다.
- 프롬프트 수정 내역을 메시지 상단에 날짜/시간과 함께 적어 두면 타임라인을 설명하기 쉽다.

주의사항 체크리스트
- 프롬프트/응답 원문은 절대 수정하지 않는다. 잘못된 부분도 그대로 캡처.
- 개인정보/키 노출 금지: API_KEY 등은 가짜 값으로 대체하거나 화면에서 가린다.
- JSON 스키마를 벗어난 응답은 “왜 잘못인지” 주석만 덧붙이고, 본문은 그대로 보이게 캡처한다.
- 가능한 한 첫 번째 응답만 캡처하고, 재시도 결과는 별도 장면으로 둔다.
