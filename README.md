# Go-LeGo Accessibility Agent

Go-LeGo의 접근성 안내 Agent를 **독립 Python 서비스로 개발한 뒤 기존 Go-LeGo Backend에 통합하기 위한 MVP**입니다.

현재 Agent는 사용자의 자연어 질문을 받아 접근성 시설, 경로, POI 사진 등을 조회하고 결과를 안전하게 전달하는 구조로 구현되어 있습니다. 최종적으로는 사용자가 지도 기능을 직접 찾지 않아도 **"어디에서 어디까지 휠체어로 안내해줘", "근처에 휠체어로 갈 수 있는 카페 있어?"**처럼 자연어로 요청할 수 있는 Agent를 목표로 합니다.

## 1. AI Agent의 역할

최종 Go-LeGo에서 Agent가 담당할 기능은 다음과 같습니다.

- **경로 안내**: 출발지, 도착지, 이동 유형을 파악하여 접근성 경로 조회
- **접근성 시설 조회**: 장애인 화장실, 엘리베이터, 경사로, 계단 등 조회
- **POI/사진 조회**: 건물 입구나 주요 POI의 등록 사진 조회
- **주변 장소 조회**: 향후 접근성이 확인된 카페·식당 등 주변 장소 조회
- **위험 정보 조회**: 향후 경로 주변의 검증된 위험 정보 조회
- **복합 질문 처리**: 경로 + 시설 + 주변 장소 등 여러 Tool을 조합
- **대화 문맥 활용**: 이전 질문의 목적지나 이동 유형 등을 다음 질문에 활용

예를 들어 다음과 같은 자연어 질문을 목표로 합니다.

```text
"본관에서 정보문화관까지 휠체어로 안내해줘."
"정보문화관 장애인 화장실 어디 있어?"
"정보문화관 주변에 휠체어로 갈 수 있는 카페 있어?"
"정보문화관 가는 길에 위험한 곳 있어?"
"본관 정문 사진 보여줘."
```

> 위험 제보 등록과 관리자 승인은 Agent의 직접 역할로 두지 않습니다. 사용자 앱/Backend에서 제보를 등록하고 검증한 뒤, Agent는 향후 검증된 위험 정보를 조회하여 안내하는 방향으로 확장합니다.

## 2. 설계 원칙

이 저장소의 Python Agent는 나중에 Go-LeGo 본 프로젝트에 통합하는 것을 전제로 계층을 분리했습니다.

```text
app/
├── api/             # HTTP/FastAPI 계층
├── application/     # Agent 유스케이스와 오케스트레이션
├── domain/          # DB/HTTP에 독립적인 핵심 모델과 Port
├── infrastructure/  # MySQL/HTTP 등 외부 시스템 Adapter
├── schemas/         # API 입력/출력 검증 모델
├── tools/           # Agent가 호출하는 기능 단위
└── core/            # 설정/DB 등 공통 인프라
```

핵심 원칙은 **라우터가 SQL이나 외부 HTTP API를 직접 실행하지 않고**, Application Service가 Tool과 Domain Port를 통해 데이터를 사용하도록 하는 것입니다.

현재 구현된 주요 Tool은 다음과 같습니다.

- `search_accessibility_facility`: 접근성 시설 및 POI 사진 조회
- Route Tool: 기존 Go-LeGo 접근성 경로 조회

향후 다음 Tool을 추가할 계획입니다.

- `nearby_accessible_place`: 주변 접근성 카페·식당 등 장소 조회
- `search_danger_info`: 경로 주변 검증된 위험 정보 조회

## 3. 현재 구현 범위

현재 Python Agent MVP는 다음 기능을 구현합니다.

### 자연어 Intent

- `TOILET`: 장애인 화장실
- `ELEVATOR`: 엘리베이터
- `RAMP`: 경사로
- `STAIR`: 계단
- `PHOTO`: POI 사진
- `ROUTE`: 경로

### 이동 유형

- `walking`
- `wheelchair`
- `stroller`
- `senior`

### 현재 위치

경로 질문에 현재 위도·경도를 전달할 수 있습니다.

### 접근성 상태

- `ACCESSIBLE`
- `NOT_ACCESSIBLE`
- `UNKNOWN`

`UNKNOWN`은 접근 가능으로 간주하지 않습니다.

## 4. 경로 안내 구조

최종적으로 가장 중요한 사용자 경험은 자연어 경로 안내입니다.

사용자가:

```text
"본관에서 정보문화관까지 휠체어로 안내해줘."
```

라고 요청하면 Agent가 다음 정보를 파악합니다.

```text
출발지 = 본관
도착지 = 정보문화관
이동 유형 = wheelchair
```

그리고 접근성 경로 Tool을 호출합니다.

```text
사용자 자연어
      ↓
AI Agent
      ↓
출발지 / 도착지 / mobilityType 추출
      ↓
Route Tool
      ↓
Go-LeGo Backend
      ↓
접근성 경로
      ↓
지도 + 경로 카드 + 안내 문구
```

현재 Route Tool은 기존 Go-LeGo Backend의 `/api/access-routes` 계약을 호출하는 구조를 기준으로 구현되어 있습니다.

## 5. 기존 프로젝트와의 관계

- 기존 Express + MySQL Agent MVP와 UI는 단계적 이전을 위해 유지합니다.
- 기존 구현은 `src/`와 `public/`에 남아 있어 동작 비교가 가능합니다.
- 신규 Python 서비스의 진입점은 `app/main.py`입니다.
- 기존 DB 변수인 `DB_*`와 MapService 계열의 `MAPSERVICE_DB_*`를 모두 읽을 수 있도록 구성했습니다.
- 사진 조회는 MapService의 `/panoramas` 경로를 사용합니다.
- 최종 Go-LeGo 통합에서는 Agent가 DB를 직접 조회하기보다 Go-LeGo Backend API를 호출하는 HTTP Adapter 구조로 전환하는 것을 목표로 합니다.

## 6. 로컬 실행

### Python Agent

```bash
python -m venv .venv

# Windows PowerShell
.\\.venv\\Scripts\\Activate.ps1

pip install -r requirements.txt
copy .env.example .env

uvicorn app.main:app --reload --port 8000
```

기본적으로 Route Tool은 다음 백엔드를 호출합니다.

```text
GOLEGO_BACKEND_BASE_URL=http://127.0.0.1:3000
```

주요 API:

- `GET /api/health`
- `POST /api/agent/chat`

Swagger:

```text
http://127.0.0.1:8000/docs
```

### 요청 예시

```json
{
  "message": "본관에서 정보문화관까지 휠체어로 가는 길",
  "mobilityType": "wheelchair"
}
```

현재 위치 기반 질문은 좌표를 함께 전달할 수 있습니다.

```json
{
  "message": "지금 여기서 정보문화관까지 가는 길",
  "mobilityType": "wheelchair",
  "currentLatitude": 37.123,
  "currentLongitude": 127.456
}
```

## 7. 현재 UI

Agent UI는 일반적인 챗봇 형태로 구성되어 있습니다.

응답은 단순 텍스트뿐 아니라 다음 결과를 카드 형태로 표시할 수 있습니다.

- 접근성 시설 카드
- 경로 카드
- POI 사진 카드

이를 통해 향후 실제 Go-LeGo 앱에서는 Agent의 답변과 지도 화면을 연결하여 **자연어 질문 → 실제 지도 기능 실행**으로 확장할 수 있습니다.

## 8. 주변 배리어프리 카페·식당

향후 사용자가 다음과 같이 질문할 수 있도록 확장합니다.

```text
"정보문화관 주변에 휠체어로 갈 수 있는 카페 있어?"
"여기 근처에 휠체어로 들어갈 수 있는 식당 찾아줘."
```

예상 처리 흐름:

```text
사용자 질문
    ↓
장소 / 현재 위치 확인
    ↓
주변 장소 검색
    ↓
접근성 정보 확인
    ↓
거리 + 접근성 상태 정리
    ↓
Agent 응답
```

중요한 점은 **일반 장소 검색 결과와 접근성이 검증된 장소를 구분하는 것**입니다.

예를 들어 접근성 정보가 확인되지 않은 장소를 Agent가 임의로 "배리어프리"라고 판단하지 않고 `UNKNOWN`으로 표시하는 것을 원칙으로 합니다.

## 9. 위험 정보 조회

향후 다음과 같은 질문을 처리할 수 있도록 확장합니다.

```text
"정보문화관 가는 길에 위험한 곳 있어?"
"휠체어로 가는데 조심해야 하는 구간 있어?"
```

목표 구조:

```text
접근성 경로 조회
      ↓
경로 주변 위험 정보 조회
      ↓
검증 상태 확인
      ↓
경로 + 위험 구간 안내
```

위험 제보 등록은 사용자 앱/Backend에서 처리하고, Agent는 검증된 위험 정보를 조회하는 역할을 담당하는 방향입니다.

## 10. 복합 질문

최종 Agent에서는 여러 기능을 하나의 질문으로 요청할 수 있도록 확장합니다.

예:

```text
"본관에서 정보문화관까지 휠체어로 가는 길 찾아주고,
가는 길에 장애인 화장실이랑 접근 가능한 카페도 알려줘."
```

Agent가 질문을 분해하여:

```text
1. 출발지 / 목적지 파악
2. 이동 유형 파악
3. 경로 조회
4. 경로 주변 시설 조회
5. 주변 카페 조회
6. 결과 종합
```

하는 구조를 목표로 합니다.

## 11. 검증

Python 코드에는 Unit Test와 Ruff 검사를 추가했습니다.

```bash
ruff check app tests
pytest
```

현재 테스트는 Intent 분석, Agent 응답, Schema validation, 현재 위치 입력 등을 검증합니다.

GitHub Actions에서도 동일한 정적 검사와 테스트를 수행합니다.

## 12. 통합 진행 상태 및 향후 계획

### Phase 1 — Agent MVP

- FastAPI Agent
- 자연어 Intent 분석
- 접근성 시설 Tool
- 접근성 Route Tool
- POI 사진 조회
- 이동 유형 처리
- 현재 위치 처리
- 챗봇 UI
- Unit Test / Ruff

### Phase 2 — Go-LeGo Backend 통합

- MySQL 직접 조회 의존성 축소
- Go-LeGo API Client 구현
- 장소 검색 API 연동
- 접근성 경로 API 연동
- 장소 접근성 API 연동
- 장소 사진 API 연동

### Phase 3 — 주변 장소 Agent

- Nearby Place Tool 추가
- 접근성 카페 검색
- 접근성 식당 검색
- 거리 기준 정렬
- 접근성 상태 및 검증 여부 표시

### Phase 4 — 위험 정보 Agent

- Danger Info Tool 추가
- 경로 주변 위험 정보 검색
- 검증된 정보 필터링
- 경로와 위험 구간을 함께 안내

### Phase 5 — LLM 기반 Tool Selection

현재 규칙 기반 Intent 분석을 LLM 기반으로 확장합니다.

```text
자연어 질문
    ↓
LLM
    ↓
의도 + 장소 + 이동 유형 + 조건 추출
    ↓
필요한 Tool 선택
    ↓
Tool 실행
    ↓
결과 종합
    ↓
자연어 응답
```

LLM은 위치나 접근성 상태를 직접 생성하지 않고, Tool이 조회한 데이터를 근거로 답변하도록 설계합니다.

### Phase 6 — 대화 Context

이전 질문의 목적지나 이동 유형을 다음 질문에서 활용합니다.

```text
사용자: "정보문화관까지 휠체어 길 찾아줘."
사용자: "거기 근처에 카페도 있어?"
```

두 번째 질문에서 "거기"를 이전 질문의 목적지인 정보문화관으로 이해하여 주변 장소를 조회하는 것을 목표로 합니다.

## 13. 최종 목표 Architecture

```text
사용자
  ↓
Go-LeGo App
  ↓
AI Agent API
  ↓
LLM / Intent & Tool Selection
  ↓
┌─────────────────────────────┐
│ Accessibility Tool          │
│ Route Tool                  │
│ Nearby Place Tool           │
│ Danger Info Tool            │
│ POI / Photo Tool            │
└─────────────────────────────┘
  ↓
Go-LeGo Backend API
  ↓
MySQL / MapService / 장소 API
  ↓
검증된 데이터
  ↓
Agent 응답
  ↓
챗봇 + 지도 + 결과 카드
```

## 14. 안전 응답 원칙

Go-LeGo Agent는 실제 이동과 접근성에 영향을 주는 정보를 다루므로 다음 원칙을 유지합니다.

- DB나 Backend에 존재하지 않는 시설 위치를 임의로 생성하지 않습니다.
- 확인되지 않은 접근성을 "가능"하다고 단정하지 않습니다.
- `UNKNOWN`은 확인되지 않은 상태로 유지합니다.
- 위험 정보는 검증 상태를 고려하여 안내합니다.
- 외부 API 장애 시 사용자가 이해할 수 있는 오류 메시지를 제공합니다.
- 경로 데이터가 없으면 데이터 부족 상태를 명확하게 안내합니다.

## 15. 참고

- Repository: `Go-LeGo-Agent`
- 기본 Branch: `main`
- FastAPI 기본 포트: `8000`
- Swagger: `/docs`
- Health Check: `GET /api/health`
- Agent API: `POST /api/agent/chat`
