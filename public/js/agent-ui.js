let mobilityType = "wheelchair";
let lastBuilding = "";

const BUILDINGS = ["정보문화관", "본관", "도서관", "디자인관", "운동장", "교수회관"];
const messages = document.querySelector("#messages");
const input = document.querySelector("#message");
const dbBadge = document.querySelector("#dbBadge");
const modeButton = document.querySelector("#modeButton");
const modeMenu = document.querySelector("#modeMenu");
const modeLabel = document.querySelector("#modeLabel");
const newChat = document.querySelector("#newChat");

function addTextMessage(text, role = "agent") {
  const row = document.createElement("div");
  row.className = `message ${role}`;
  row.innerHTML = `
    <span class="avatar">${role === "agent" ? "G" : "나"}</span>
    <div class="bubble"></div>
  `;
  row.querySelector(".bubble").textContent = normalizeAnswer(text);
  messages.append(row);
  scrollMessages();
  return row;
}

function addWelcome() {
  const welcome = document.createElement("div");
  welcome.className = "welcome";
  welcome.innerHTML = `
    <div class="welcome-icon">G</div>
    <h2>어디로 가고 싶으신가요?</h2>
    <p>
      고르고가 등록된 접근성 시설과 경로를 확인해드릴게요.<br>
      모르는 정보는 추측하지 않고, 확인된 데이터만 안내합니다.
    </p>
  `;
  messages.append(welcome);
}

function addPhotoCards(items) {
  const group = document.createElement("div");
  group.className = "photo-list";

  items.forEach((item) => {
    if (!item.photoUrl) return;

    const card = document.createElement("article");
    card.className = "photo-card";
    card.innerHTML = `
      <div class="photo-frame">
        <img src="${escapeHtml(item.photoUrl)}" alt="${escapeHtml(item.name)} 사진" loading="lazy">
      </div>
      <div class="photo-caption">
        <div>
          <span class="type-label">등록된 현장 사진</span>
          <h3>${escapeHtml(item.name)}</h3>
          <p>${escapeHtml(item.description || item.floor || "등록된 POI 사진")}</p>
        </div>
        <button type="button" class="photo-open" data-url="${escapeHtml(item.photoUrl)}">크게 보기</button>
      </div>
    `;
    group.append(card);
  });

  group.addEventListener("click", (event) => {
    const button = event.target.closest(".photo-open");
    if (!button) return;
    window.open(button.dataset.url, "_blank", "noopener,noreferrer");
  });

  if (group.children.length) {
    messages.append(group);
    scrollMessages();
  }
}

function addFacilityCards(items) {
  if (!items.length) return;

  const group = document.createElement("div");
  group.className = "facility-list";

  items.forEach((item) => {
    const card = document.createElement("article");
    card.className = "facility-card";
    const status = statusInfo(item.wheelchairAccessStatus);
    card.innerHTML = `
      <div class="card-top">
        <span class="type-label">${escapeHtml(typeLabel(item.type))}</span>
        <span class="status ${status.className}">${status.label}</span>
      </div>
      <h3>${escapeHtml(item.name)}</h3>
      <p class="location"><b>위치</b> ${escapeHtml(item.floor || "층 정보 없음")}${item.description ? ` · ${escapeHtml(item.description)}` : ""}</p>
      <div class="card-actions">
        <button type="button" data-action="detail" data-facility="${escapeHtml(item.name)}">상세 정보</button>
        <button type="button" data-action="report" data-facility="${escapeHtml(item.name)}">정보 제보</button>
      </div>
    `;
    group.append(card);
  });

  group.addEventListener("click", (event) => {
    const button = event.target.closest("button");
    if (!button) return;
    const facility = button.dataset.facility;

    if (button.dataset.action === "detail") {
      addTextMessage(
        `“${facility}”는 현재 등록된 POI 설명과 접근성 상태를 기준으로 안내하고 있습니다. 사진, 문 폭, 비상벨 등 추가 정보는 현장 조사 후 연결할 수 있습니다.`
      );
    }

    if (button.dataset.action === "report") {
      addTextMessage(
        `“${facility}”의 위치나 접근성 정보 제보 기능은 기존 제보 API와 연결하는 다음 통합 단계에서 제공할 예정입니다.`
      );
    }
  });

  messages.append(group);
  scrollMessages();
}

function addRouteCards(routes) {
  if (!routes.length) return;

  const group = document.createElement("div");
  group.className = "route-list";

  routes.forEach((route, index) => {
    const features = route.features || {};
    const featureItems = [
      ["계단", features.stairs],
      ["경사로", features.ramps],
      ["엘리베이터", features.elevators],
      ["횡단보도", features.crosswalks],
    ].filter(([, count]) => Number(count) > 0);

    const card = document.createElement("article");
    card.className = "route-card";
    card.innerHTML = `
      <div class="card-top">
        <span class="type-label">${index === 0 ? "추천 경로" : `대안 경로 ${index}`}</span>
        ${route.dangerCount ? `<span class="status unknown">위험 지점 ${route.dangerCount}곳</span>` : ""}
      </div>
      <h3>${escapeHtml(route.title || "접근성 경로")}</h3>
      <div class="route-summary">
        <span class="route-stat"><strong>${formatDistance(route.distance)}</strong>거리</span>
        <span class="route-stat"><strong>${formatDuration(route.duration)}</strong>예상</span>
        <span class="route-stat"><strong>${route.path?.length || 0}</strong>주요 지점</span>
      </div>
      <div class="route-features">
        ${featureItems.map(([label, count]) => `<span class="route-feature">${label} ${count}</span>`).join("")}
      </div>
    `;
    group.append(card);
  });

  messages.append(group);
  scrollMessages();
}

function showThinking(intentHint) {
  const steps = loadingSteps(intentHint);
  const row = document.createElement("div");
  row.className = "message agent thinking";
  row.innerHTML = `
    <span class="avatar">G</span>
    <div class="bubble">
      <div class="thinking-content">
        <span class="dot-loader"><i></i><i></i><i></i></span>
        <span class="thinking-text"></span>
      </div>
    </div>
  `;

  const title = row.querySelector(".thinking-text");
  let index = 0;
  title.textContent = steps[index];

  const timer = setInterval(() => {
    index = (index + 1) % steps.length;
    title.textContent = steps[index];
  }, 650);

  messages.append(row);
  scrollMessages();
  return {row, timer};
}

async function ask(rawMessage) {
  const suppliedBuilding = findBuilding(rawMessage);
  const isFacilityQuestion = /화장실|엘리베이터|엘베|승강기|경사로|램프|계단/.test(rawMessage);
  const effectiveMessage = !suppliedBuilding && lastBuilding && isFacilityQuestion
    ? `${lastBuilding} ${rawMessage}`
    : rawMessage;

  addTextMessage(rawMessage, "user");
  const thinking = showThinking(detectIntentHint(effectiveMessage));
  const start = Date.now();

  try {
    const response = await fetch("/api/agent/chat", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        message: effectiveMessage,
        mobilityType: mobilityType,
      }),
    });

    const data = await response.json();

    if (!response.ok || !data.ok) {
      throw new Error(data.detail || data.error || "Agent 요청에 실패했습니다.");
    }

    const elapsed = Date.now() - start;
    await delay(Math.max(0, 650 - elapsed));

    clearInterval(thinking.timer);
    thinking.row.remove();

    const responseBuilding = findBuilding(effectiveMessage)
      || findBuilding(data.items?.[0]?.name || "");

    if (responseBuilding) {
      setLastBuilding(responseBuilding);
    }

    addTextMessage(data.answer);

    if (data.items?.length) {
      if (data.intent === "PHOTO") {
        addPhotoCards(data.items);
      } else {
        addFacilityCards(data.items);
      }
    }

    if (data.routes?.length) {
      addRouteCards(data.routes);
    }

    updateConnection(true);
  } catch (error) {
    clearInterval(thinking.timer);
    thinking.row.remove();
    addTextMessage(
      `요청을 처리하지 못했습니다.\n${error.message}\n\nAPI 서버와 DB 연결 상태를 확인해 주세요.`
    );
  }
}

async function checkDatabase() {
  try {
    const response = await fetch("/api/health");
    const data = await response.json();

    if (!response.ok || !data.ok) {
      throw new Error(data.detail || data.error || "Health check failed");
    }

    updateConnection(true, data.database ? `DB ${data.database}` : "Agent 연결됨");
  } catch (error) {
    updateConnection(false);
    addTextMessage(
      `Agent 연결을 확인하지 못했습니다.\n${error.message}\n\n서버가 http://127.0.0.1:8000 에서 실행 중인지 확인해 주세요.`
    );
  }
}

function updateConnection(connected, label) {
  dbBadge.classList.toggle("connected", connected);
  dbBadge.classList.toggle("failed", !connected);
  dbBadge.innerHTML = `<span class="status-dot"></span>${connected ? (label || "Agent 연결됨") : "연결 실패"}`;
}

function updateMode(mode) {
  mobilityType = mode;
  const labels = {
    wheelchair: "휠체어",
    walking: "일반 이동",
    stroller: "유모차",
    senior: "어르신",
  };
  const icons = {
    wheelchair: "♿",
    walking: "🚶",
    stroller: "🛒",
    senior: "🧓",
  };
  modeLabel.textContent = labels[mode] || "휠체어";
  modeButton.querySelector(".mode-icon").textContent = icons[mode] || "♿";
  modeMenu.hidden = true;
}

function resetChat() {
  messages.replaceChildren();
  lastBuilding = "";
  addWelcome();
  addTextMessage("안녕하세요. 저는 고르고예요.\n화장실, 엘리베이터, 경사로 또는 휠체어 경로를 물어보세요.");
}

function setLastBuilding(building) {
  lastBuilding = building;
}

function findBuilding(text) {
  return BUILDINGS.find((building) => String(text).includes(building)) || "";
}

function scrollMessages() {
  messages.scrollTop = messages.scrollHeight;
}

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function detectIntentHint(text) {
  if (/화장실/.test(text)) return "TOILET";
  if (/엘리베이터|엘베|승강기/.test(text)) return "ELEVATOR";
  if (/경사로|램프/.test(text)) return "RAMP";
  if (/계단/.test(text)) return "STAIR";
  if (/경로|길찾기|가는길|어떻게가|갈수|이동|까지/.test(text)) return "ROUTE";
  return "UNKNOWN";
}

function loadingSteps(intent) {
  const target = {
    TOILET: "장애인 화장실",
    ELEVATOR: "엘리베이터",
    RAMP: "경사로",
    STAIR: "계단",
    ROUTE: "접근성 경로",
  }[intent] || "질문";

  return [
    `${target} 질문을 분석하고 있어요.`,
    "등록된 Go-LeGo 데이터를 확인하고 있어요.",
    "확인된 결과를 안전하게 정리하고 있어요.",
  ];
}

function typeLabel(type) {
  return {
    accessible_toilet: "장애인 화장실",
    elevator: "엘리베이터",
    ramp: "경사로",
    stair: "계단",
  }[type] || "접근성 시설";
}

function statusInfo(status) {
  if (status === "ACCESSIBLE") {
    return {label: "접근 가능 확인", className: "accessible"};
  }

  if (status === "NOT_ACCESSIBLE") {
    return {label: "접근 어려움", className: "not-accessible"};
  }

  return {label: "현장 확인 필요", className: "unknown"};
}

function formatDistance(distance) {
  const value = Number(distance) || 0;
  return value >= 1000 ? `${(value / 1000).toFixed(1)}km` : `${Math.round(value)}m`;
}

function formatDuration(duration) {
  return `${Math.round(Number(duration) || 0)}분`;
}

function normalizeAnswer(value) {
  return String(value ?? "").replace(/\\\\n/g, "\n");
}

function escapeHtml(value) {
  return String(value).replace(/[&<>'"]/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    "'": "&#39;",
    '"': "&quot;",
  }[char]));
}

document.querySelector("#chatForm").addEventListener("submit", (event) => {
  event.preventDefault();
  const question = input.value.trim();
  if (!question) return;
  input.value = "";
  ask(question);
});

document.querySelectorAll("[data-question]").forEach((button) => {
  button.addEventListener("click", () => ask(button.dataset.question));
});

modeButton.addEventListener("click", () => {
  const rect = modeButton.getBoundingClientRect();
  modeMenu.hidden = !modeMenu.hidden;
  if (!modeMenu.hidden) {
    modeMenu.style.left = `${rect.left}px`;
    modeMenu.style.bottom = `${window.innerHeight - rect.top + 7}px`;
  }
});

document.querySelectorAll("[data-mode]").forEach((button) => {
  button.addEventListener("click", () => {
    updateMode(button.dataset.mode);
    addTextMessage(
      `이동 모드를 “${button.textContent.replace(/^[^가-힣A-Za-z]+/, "").trim()}”로 변경했어요.`
    );
  });
});

document.addEventListener("click", (event) => {
  if (!modeMenu.hidden && !modeMenu.contains(event.target) && !modeButton.contains(event.target)) {
    modeMenu.hidden = true;
  }
});

newChat.addEventListener("click", resetChat);

addWelcome();
addTextMessage(
  "안녕하세요. 저는 고르고예요.\n화장실, 엘리베이터, 경사로 또는 휠체어 경로를 물어보세요."
);
checkDatabase();
