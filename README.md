# Go-LeGo Accessibility Agent

Go-LeGo의 접근성 안내 Agent를 **독립 Python 서비스로 개발한 뒤 기존 Go-LeGo Backend에 이식하기 위한 MVP**입니다.

## 1. 설계 원칙

이 저장소의 Python Agent는 나중에 Go-LeGo 본 프로젝트에 붙여넣는 것을 전제로 다음 계층으로 분리했습니다.

```
app/
├── api/             # HTTP/FastAPI 계층
├── application/     # Agent 유스케이스와 오케스트레이션
├── domain/          # DB/HTTP에 독립적인 핵심 모델과 Port
├── infrastructure/  # MySQL/HTTP 등 외부 시스템 Adapter
├── schemas/         # API 입력/출력 검증 모델
└── core/             # 설정/DB 등 공통 인프라
```

핵심 원칙은 **라우터가 SQL이나 외부 HTTP API를 직접 실행하지 않고**, Application Service가 Domain Port를 통해 데이터를 사용하도록 하는 것입니다.

현재는 다음 Tool을 제공합니다.

- `search_accessibility_facility`: 접근성 시설 조회
- `find_accessible_route`: 기존 Go-LeGo `/api/access-routes` 경로 조회

## 2. 기존 프로젝트와의 관계

- 기존 Express + MySQL Agent MVP와 UI는 당장 삭제하지 않습니다.
- 기존 구현은 `src/`와 `public/`에 남아 있어 동작 비교와 단계적 이전이 가능합니다.
- 신규 Python 서비스의 진입점은 `app/main.py`입니다.
- 기존 DB 변수인 `DB_*`와 MapService 계열의 `MAPSERVICE_DB_*`를 모두 읽을 수 있도록 구성했습니다.
- Route Tool은 `GOLEGO_BACKEND_BASE_URL`로 기존 Go-LeGo Backend를 호출합니다.

## 3. 로컬 실행

### Python Agent

```bash
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --port 8000
```

기본적으로 Route Tool은 다음 백엔드를 호출합니다.

```
GOLEGO_BACKEND_BASE_URL=http://127.0.0.1:3000
```

주요 API:

- `GET /api/health`
- `POST /api/agent/chat`

예시:

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

## 4. 검증

Python 코드에는 Unit Test와 Ruff 검사를 추가했습니다.

```bash
ruff check app tests
pytest
```

GitHub Actions에서도 동일한 검증을 수행합니다.

## 5. 통합 진행 상태

1. 현재 MySQL Repository Adapter의 실제 DB 스키마를 확인했습니다.
2. **접근성 시설 Tool을 MySQL에 연결했습니다.**
3. **경로 탐색 Tool을 기존 Go-LeGo `/api/access-routes` 계약과 연결했습니다.**
4. 다음 단계로 위험 제보 Tool을 추가하되 `PENDING → VALID/REJECTED → RESOLVED` lifecycle을 그대로 사용합니다.
5. LLM Provider는 Tool 호출 계층과 분리해 추가합니다. LLM이 시설 위치나 경로를 직접 만들어내지 못하도록 조회 결과를 근거 데이터로 제한합니다.
6. Go-LeGo 본 Backend와 최종 통합할 때 DB 직접 접근 대신 HTTP Adapter를 기준으로 전환할 수 있도록 Port를 유지합니다.

## 6. 안전 응답 원칙

DB나 기존 Go-LeGo Backend에 존재하지 않는 시설 위치, 경로, 접근성 상태를 Agent가 임의로 생성하지 않습니다. `UNKNOWN`은 확인되지 않은 상태로 유지하며, 특히 휠체어 이동에서는 확인되지 않은 정보를 접근 가능하다고 단정하지 않습니다.
