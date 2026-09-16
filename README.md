# 고르고 접근성 안내 Agent MVP

기존 지도 프로젝트와 분리된 독립 MySQL 기반 Agent입니다. 외부 AI API와 Kakao 지도 없이도 실행되며, `barrier_free_db`의 `poi`, `facility`, `place_accessibility`를 조회합니다.

## 이번 UI 고도화 기능

- 자연스러운 단계형 로딩: 질문 분석 → POI 검색 → 접근성 상태 확인
- 실제 DB 응답이 빨라도 최소 0.95초간 로딩 상태를 보여주는 채팅 UX
- 시설별 결과 카드와 `접근 가능 확인` / `현장 확인 필요` / `접근 어려움` 배지
- 직전 대화 건물 기억: 예) 정보문화관 화장실 검색 후 `엘리베이터도 있어?` 질문
- 우측 Agent 처리 로그: 질문 의도, 검색 건수, 안전 응답 생성 상태
- `/api/health`로 MySQL 연결 상태를 화면에서 확인

## 실행

```powershell
Copy-Item .env.example .env
npm install
npm start
```

`.env`에는 실제 MySQL 접속 정보를 넣습니다. 변수명은 기존 AccessNavWeb과 호환됩니다.

```env
PORT=3000
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PASSWORD=실제_MySQL_비밀번호
DB_NAME=barrier_free_db

MAPSERVICE_DB_HOST=127.0.0.1
MAPSERVICE_DB_PORT=3306
MAPSERVICE_DB_USER=root
MAPSERVICE_DB_PASSWORD=실제_MySQL_비밀번호
MAPSERVICE_DB_NAME=barrier_free_db
```

브라우저에서 열기:

```text
http://localhost:3000
```

## DB 연결 확인

```text
http://localhost:3000/api/health
```

정상 응답:

```json
{"ok":true,"database":"barrier_free_db","connected":true}
```

## 발표 시연 순서

1. 우측 상단 `DB 연결됨: barrier_free_db` 표시 확인
2. `정보문화관 장애인 화장실 어디 있어?` 질문
3. 로딩 단계와 `ACCESSIBLE` 시설 카드 확인
4. 이어서 `엘리베이터도 있어?` 질문
5. 직전 건물인 정보문화관을 기억해 검색하는지 확인
6. 휠체어 모드 전환 후 `본관 3층 화장실 어디 있어?` 질문
7. `UNKNOWN`을 `현장 확인 필요`로 표시하는 안전 정책 확인

## 다음 고도화 후보

- 시설 사진과 실내 안내 이미지 추가
- 현 위치 기반 가까운 시설 거리 정렬
- 제보 버튼을 기존 `/api/accessibility-reports` API와 연결
- `stair`를 제외하고 `ramp`, `elevator`, `path`를 우선하는 휠체어 경로 탐색
- 문서 임베딩(RAG)으로 교내 편의시설 이용 기준과 FAQ 응답 보강

## Git 커밋 메시지

```text
feat: enhance agent chat UX with loading states and accessibility result cards
```
