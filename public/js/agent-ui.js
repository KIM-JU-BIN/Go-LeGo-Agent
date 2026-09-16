let mobilityType = 'walking';
let lastBuilding = '';

const BUILDINGS = ['정보문화관', '본관', '도서관', '디자인관', '운동장', '교수회관'];
const messages = document.querySelector('#messages');
const input = document.querySelector('#message');
const dbBadge = document.querySelector('#dbBadge');
const contextBuilding = document.querySelector('#contextBuilding');
const processLog = document.querySelector('#processLog');
const resultCount = document.querySelector('#resultCount');

function addTextMessage(text, role = 'agent') {
  const row = document.createElement('div');
  row.className = `message ${role}`;
  row.innerHTML = `<span class="avatar">${role === 'agent' ? 'AI' : 'ME'}</span><div class="bubble"></div>`;
  row.querySelector('.bubble').textContent = text;
  messages.append(row);
  scrollMessages();
  return row;
}

function addFacilityCards(items) {
  if (!items.length) return;
  const group = document.createElement('div');
  group.className = 'facility-list';

  items.forEach((item) => {
    const card = document.createElement('article');
    card.className = 'facility-card';
    const status = statusInfo(item.wheelchairAccessStatus);
    card.innerHTML = `
      <div class="facility-card-top">
        <span class="type-label">${typeLabel(item.type)}</span>
        <span class="status ${status.className}">${status.label}</span>
      </div>
      <h3>${escapeHtml(item.name)}</h3>
      <p class="location"><b>위치</b> ${escapeHtml(item.floor || '층 정보 없음')}${item.description ? ` · ${escapeHtml(item.description)}` : ''}</p>
      <div class="card-actions">
        <button type="button" class="detail-button" data-facility="${escapeHtml(item.name)}">상세 정보</button>
        <button type="button" class="report-button" data-facility="${escapeHtml(item.name)}">정보 제보</button>
      </div>`;
    group.append(card);
  });

  group.addEventListener('click', (event) => {
    const facility = event.target.dataset.facility;
    if (!facility) return;
    if (event.target.classList.contains('detail-button')) {
      addTextMessage(`“${facility}”의 상세 정보는 현재 POI 설명과 접근성 상태를 기준으로 표시하고 있습니다. 사진, 문 폭, 비상벨 정보는 현장 조사 후 추가할 예정입니다.`);
    }
    if (event.target.classList.contains('report-button')) {
      addTextMessage(`“${facility}”의 위치 또는 접근성 정보 제보 화면은 다음 통합 단계에서 기존 AccessNavWeb 제보 API와 연결할 예정입니다.`);
    }
  });
  messages.append(group);
  scrollMessages();
}

function showThinking(intentHint) {
  const steps = loadingSteps(intentHint);
  const row = document.createElement('div');
  row.className = 'message agent thinking-row';
  row.innerHTML = `<span class="avatar">AI</span><div class="bubble thinking"><span class="dot-loader"><i></i><i></i><i></i></span><strong></strong><small></small></div>`;
  const title = row.querySelector('strong');
  const detail = row.querySelector('small');
  let index = 0;
  title.textContent = steps[index].title;
  detail.textContent = steps[index].detail;
  const timer = setInterval(() => {
    index = (index + 1) % steps.length;
    title.textContent = steps[index].title;
    detail.textContent = steps[index].detail;
  }, 550);
  messages.append(row);
  scrollMessages();
  return { row, timer };
}

async function ask(rawMessage) {
  const suppliedBuilding = findBuilding(rawMessage);
  const isFacilityQuestion = /화장실|엘리베이터|엘베|승강기|경사로|램프|계단/.test(rawMessage);
  const effectiveMessage = !suppliedBuilding && lastBuilding && isFacilityQuestion
    ? `${lastBuilding} ${rawMessage}`
    : rawMessage;

  addTextMessage(rawMessage, 'user');
  if (!suppliedBuilding && lastBuilding && isFacilityQuestion) {
    updateProcess(['직전 대화 건물 확인 완료', `${lastBuilding} 기준으로 후속 질문 검색`, '시설 정보 조회 준비 완료']);
  }

  const thinking = showThinking(detectIntentHint(effectiveMessage));
  const start = Date.now();
  updateProcess(['질문 의도 분석 중', 'MySQL POI 데이터 검색 중', '접근성 상태 결합 중']);

  try {
    const response = await fetch('/api/agent/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: effectiveMessage, mobilityType }),
    });
    const data = await response.json();
    if (!response.ok || !data.ok) throw new Error(data.detail || data.error || 'Agent 요청에 실패했습니다.');

    // 실제 DB가 빠르게 응답해도 사용자가 처리 과정을 인지할 수 있도록 최소 표시 시간을 둡니다.
    const elapsed = Date.now() - start;
    await delay(Math.max(0, 950 - elapsed));
    clearInterval(thinking.timer);
    thinking.row.remove();

    const responseBuilding = findBuilding(effectiveMessage) || findBuilding(data.items?.[0]?.name || '');
    if (responseBuilding) setLastBuilding(responseBuilding);
    updateProcess([
      `질문 의도 인식: ${intentLabel(data.intent)}`,
      `MySQL 검색 완료: ${data.items.length}건`,
      '접근성 상태 확인 및 안전 응답 생성 완료',
    ]);
    resultCount.textContent = `${data.items.length}건 조회`;
    addTextMessage(data.answer);
    addFacilityCards(data.items);
  } catch (error) {
    clearInterval(thinking.timer);
    thinking.row.remove();
    updateProcess(['요청 처리 실패', '서버 및 MySQL 연결 상태 확인 필요']);
    resultCount.textContent = '조회 실패';
    addTextMessage(`요청을 처리하지 못했습니다.\n${error.message}`);
  }
}

async function checkDatabase() {
  try {
    const response = await fetch('/api/health');
    const data = await response.json();
    if (!response.ok || !data.ok) throw new Error(data.detail || data.error);
    dbBadge.textContent = `DB 연결됨: ${data.database}`;
    dbBadge.className = 'badge connected';
  } catch (error) {
    dbBadge.textContent = 'DB 연결 실패';
    dbBadge.className = 'badge failed';
    addTextMessage(`MySQL 연결을 확인하지 못했습니다.\n${error.message}\n\n.env의 DB_PASSWORD와 DB_NAME을 확인해 주세요.`);
  }
}

function updateProcess(lines) {
  processLog.replaceChildren(...lines.map((line, index) => {
    const li = document.createElement('li');
    li.className = index === lines.length - 1 ? 'complete' : '';
    li.textContent = line;
    return li;
  }));
}
function setLastBuilding(building) { lastBuilding = building; contextBuilding.textContent = `${building} 기준으로 대화 중`; }
function findBuilding(text) { return BUILDINGS.find((building) => String(text).includes(building)) || ''; }
function delay(ms) { return new Promise((resolve) => setTimeout(resolve, ms)); }
function scrollMessages() { messages.scrollTop = messages.scrollHeight; }
function detectIntentHint(text) { if (/화장실/.test(text)) return 'TOILET'; if (/엘리베이터|엘베|승강기/.test(text)) return 'ELEVATOR'; if (/경사로|램프/.test(text)) return 'RAMP'; if (/계단/.test(text)) return 'STAIR'; return 'UNKNOWN'; }
function loadingSteps(intent) { const target = {TOILET:'화장실',ELEVATOR:'엘리베이터',RAMP:'경사로',STAIR:'계단'}[intent] || '시설'; return [{title:'질문을 분석하고 있어요.',detail:'찾으려는 시설 유형을 확인하고 있습니다.'},{title:`등록된 ${target} 정보를 검색하고 있어요.`,detail:'MySQL POI 데이터를 조회하고 있습니다.'},{title:'접근성 상태를 확인하고 있어요.',detail:'확인되지 않은 정보는 안전하다고 단정하지 않습니다.'}]; }
function intentLabel(intent) { return {TOILET:'장애인 화장실',ELEVATOR:'엘리베이터',RAMP:'경사로',STAIR:'계단',UNKNOWN:'일반 문의'}[intent] || '일반 문의'; }
function typeLabel(type) { return {accessible_toilet:'장애인 화장실',elevator:'엘리베이터',ramp:'경사로',stair:'계단'}[type] || '시설'; }
function statusInfo(status) { return status === 'ACCESSIBLE' ? {label:'접근 가능 확인',className:'accessible'} : status === 'NOT_ACCESSIBLE' ? {label:'접근 어려움',className:'not-accessible'} : {label:'현장 확인 필요',className:'unknown'}; }
function escapeHtml(value) { return String(value).replace(/[&<>'"]/g, (char) => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[char])); }

document.querySelector('#chatForm').addEventListener('submit', (event) => { event.preventDefault(); const question = input.value.trim(); if (!question) return; input.value = ''; ask(question); });
document.querySelectorAll('[data-question]').forEach((button) => button.addEventListener('click', () => ask(button.dataset.question)));
document.querySelectorAll('[data-mode]').forEach((button) => button.addEventListener('click', () => { mobilityType = button.dataset.mode; document.querySelectorAll('[data-mode]').forEach((item) => item.classList.toggle('active', item === button)); addTextMessage(mobilityType === 'wheelchair' ? '휠체어 이동 모드로 변경했습니다. 접근 상태가 확인되지 않은 시설은 현장 확인이 필요합니다.' : '일반 이동 모드로 변경했습니다.'); }));

addTextMessage('안녕하세요. 고르고 접근성 안내 Agent입니다.\n\n장애인 화장실, 엘리베이터, 경사로, 계단 정보를 질문해 주세요.');
checkDatabase();
