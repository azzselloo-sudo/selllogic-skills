# 셀로직 스킬 (Claude Code 스터디 심화반 교보재)

Claude Code 스터디 심화반 수강생용 스킬 묶음. 각 단계 실습에서 이 스킬을 열어 구조를 뜯어보고,
자기 버전으로 고쳐 쓰는 것이 과제다.

## 설치

Claude Code 에서:

```
/plugin marketplace add azzselloo-sudo/selllogic-skills
/plugin install selllogic-toolkit@selllogic-skills
/plugin install selllogic-free@selllogic-skills
```

플러그인은 넷이다. 필요한 것만 설치한다.

| 플러그인 | 내용 | 출처 |
|---|---|---|
| `selllogic-toolkit` | 심화반 교보재 10종 | 스터디 자체 제작 |
| `selllogic-marketing` | 마케팅 스킬 49종 + 활용 가이드 | MIT · Corey Haines |
| `selllogic-design` | 프론트 디자인 톤 7종 + 활용 가이드 | MIT · Leonxlnx |
| `selllogic-free` | 1인 사업자용 무료 절차 스킬 4종 | 셀로직 자체 제작 |

`selllogic-marketing` 과 `selllogic-design` 은 **원문 그대로**다. 고치지 않았으므로 업스트림이 갱신되면
그대로 따라갈 수 있다. 대신 각 플러그인의 `USAGE.md` 에 "언제 무엇을 켜는지 + 실전 함정"을 적어 두었다.
스킬을 받는 것보다 그 문서를 읽는 쪽이 먼저다.

설치 후 `/plugin` 으로 확인한다.

## selllogic-toolkit 에 담긴 스킬

| 스킬 | 무엇을 하나 | 관련 단계 |
|---|---|---|
| `prd-writing` | 제품 요구사항 문서를 근거 있게 쓴다 | 1 규칙화 |
| `doc-build` | 견적서·보고서·제안서를 HTML/PDF 로 | 4 나만의 스킬 |
| `gsheet-report` | 구글 시트를 코드로 만들고 서식을 고정 | 4 나만의 스킬 |
| `slack-automation` | 슬랙을 코드로 읽고 쓴다 | 6 도구 연결 |
| `shop-crawler` | 상품 정보를 긁어 표로 만든다 | 6 도구 연결 |
| `smart-ocr` | 이미지·PDF 에서 글자를 뽑는다 | 6 도구 연결 |
| `windows-ui-automation` | 윈도우 데스크톱 앱을 자동 조작 | 7 병렬 |
| `ir-search` | 지원사업·공모를 조사하고 적합성을 판정 | 선택 |
| `agent-boost` | 상황별로 어떤 스킬을 켤지 고르는 라우팅표 | 전체 |
| `hermes-setup` | 내 슬랙에 24시간 도는 AI 비서를 붙인다 | 10 자립 |

## selllogic-free 에 담긴 스킬

알면 1분, 모르면 반나절 걸리는 절차 지식을 스킬로 묶었다. 자기 계정으로 바로 쓸 수 있다.

```
/plugin install selllogic-free@selllogic-skills
```

| 스킬 | 무엇을 하나 |
|---|---|
| `naver-commerce-api-setup` | 스마트스토어 커머스API 앱 발급. 영수증 캡차가 계속 틀렸다고 나오는 이유, 허용 IP 403, API 상품 등록, 쇼핑 커넥트 |
| `smartstore-nbaesong-fassto` | N배송을 파스토 풀필먼트로 켜고 점검. 세 곳이 모두 켜져야 동작하는 지점 |
| `repo-secret-scan` | 저장소를 남에게 주거나 공개하기 전에 비밀키·고객명·내부 경로를 지금 파일과 커밋 이력까지 검사(스크립트 포함) |
| `windows-task-scheduler-silent-fail` | 윈도우 예약 작업이 결과 0 인데 안 도는 경우의 원인과 등록·검증 절차 |

## 쓰는 법

스킬은 "이 스킬 써줘"라고 부르지 않아도 된다. 각 스킬의 `description` 에 적힌 상황이 오면
Claude 가 알아서 켠다. 안 켜지면 그 문장에 트리거 단어를 넣어 말하거나 `/스킬명` 으로 직접 부른다.

## 고쳐 쓰기

이 스킬들은 완성품이 아니라 **뼈대**다. 그대로 쓰는 것보다 자기 업무에 맞게 고치는 쪽이 과제에 가깝다.

1. `~/.claude/skills/<이름>/SKILL.md` 로 복사
2. 내 업무 절차·함정으로 내용 교체
3. 실제로 발동하는지 확인
4. 4단계 과제로 제출

## 주의

- `selllogic-toolkit` 스킬 안의 경로·계정은 전부 `<자리표시자>` 다. 자기 값으로 바꿔야 동작한다
- 토큰·키를 스킬 파일에 적지 않는다. 환경변수로 넣는다
- `selllogic-marketing`·`selllogic-design` 은 영어권 기준으로 쓰인 원문이다. 한국 시장에 맞게 다시 지시해야 한다
- 재배포분의 라이선스(MIT)와 저작권 고지는 각 플러그인 폴더의 `LICENSE` 에 있다. 지우지 않는다
