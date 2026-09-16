const INTENT_CONFIG = {
  TOILET: { label: '장애인 화장실', poiTypes: ['accessible_toilet'] },
  ELEVATOR: { label: '엘리베이터', poiTypes: ['elevator'] },
  RAMP: { label: '경사로', poiTypes: ['ramp'] },
  STAIR: { label: '계단', poiTypes: ['stair'] },
};

async function buildAgentResponse(db, { message, mobilityType }) {
  const intent = detectIntent(message);
  if (!intent) {
    return {
      intent: 'UNKNOWN',
      items: [],
      answer: '찾으려는 시설을 조금 더 구체적으로 말씀해 주세요.\n\n예: “정보문화관 장애인 화장실 어디 있어?”, “본관 엘리베이터 알려줘”, “도서관 경사로 찾아줘”',
    };
  }

  const facilities = await searchFacilities(db, intent, message);
  return {
    intent,
    items: facilities.map(toPublicItem),
    answer: makeAnswer({ intent, facilities, mobilityType }),
  };
}

async function searchFacilities(db, intent, message) {
  const config = INTENT_CONFIG[intent];
  const placeholders = config.poiTypes.map(() => '?').join(', ');
  const [rows] = await db.execute(
    `SELECT
       p.poi_id, p.poi_name, p.poi_type, p.latitude, p.longitude,
       p.floor_info, p.description,
       f.facility_name, f.facility_category, f.open_hours, f.facility_features,
       pa.wheelchair_access_status, pa.updated_at
     FROM poi p
     LEFT JOIN facility f ON f.poi_id = p.poi_id
     LEFT JOIN place_accessibility pa ON pa.poi_id = p.poi_id
     WHERE p.poi_type IN (${placeholders})
     ORDER BY p.poi_name ASC`,
    config.poiTypes
  );

  const buildingWords = extractBuildingWords(message);
  const ranked = rows
    .map((row) => ({ row, score: scoreRow(row, buildingWords) }))
    .filter(({ score }) => buildingWords.length === 0 || score > 0)
    .sort((a, b) => b.score - a.score || a.row.poi_name.localeCompare(b.row.poi_name, 'ko'))
    .map(({ row }) => row);

  return ranked.slice(0, 5);
}

function detectIntent(message) {
  const text = normalize(message);
  if (/화장실|toilet/.test(text)) return 'TOILET';
  if (/엘리베이터|엘베|승강기/.test(text)) return 'ELEVATOR';
  if (/경사로|램프|ramp/.test(text)) return 'RAMP';
  if (/계단|stair/.test(text)) return 'STAIR';
  return null;
}

function extractBuildingWords(message) {
  const knownBuildings = ['정보문화관', '본관', '도서관', '디자인관', '운동장', '교수회관'];
  return knownBuildings.filter((building) => normalize(message).includes(normalize(building)));
}

function scoreRow(row, buildingWords) {
  if (!buildingWords.length) return 1;
  const haystack = normalize([row.poi_name, row.description, row.facility_name].filter(Boolean).join(' '));
  return buildingWords.reduce((score, building) => score + (haystack.includes(normalize(building)) ? 10 : 0), 0);
}

function makeAnswer({ intent, facilities, mobilityType }) {
  const label = INTENT_CONFIG[intent].label;
  if (!facilities.length) {
    return `등록된 데이터에서 요청하신 ${label} 정보를 찾지 못했습니다.\n\n정확하지 않은 위치를 만들어 안내하지 않습니다. 현장 확인 후 접근성 제보로 등록해 주세요.`;
  }

  const lines = [`등록된 ${label} ${facilities.length}곳을 찾았습니다.`, ''];
  facilities.forEach((item, index) => {
    lines.push(`${index + 1}. ${item.poi_name}`);
    lines.push(`- 위치: ${item.floor_info || '층 정보 없음'}${item.description ? ` / ${item.description}` : ''}`);
    lines.push(`- 휠체어 접근 상태: ${accessibilityLabel(item.wheelchair_access_status)}`);
    lines.push('');
  });

  if (mobilityType === 'wheelchair') {
    lines.push('휠체어 이동 안내: UNKNOWN 상태는 문 폭·단차·공사 여부가 검증되지 않았으므로 현장 확인이 필요합니다.');
  } else {
    lines.push('필요하면 휠체어 모드로 전환해 접근성 상태를 함께 확인할 수 있습니다.');
  }
  return lines.join('\n').trim();
}

function accessibilityLabel(status) {
  if (status === 'ACCESSIBLE') return '확인됨 (ACCESSIBLE)';
  if (status === 'NOT_ACCESSIBLE') return '접근 어려움 (NOT_ACCESSIBLE)';
  return '확인 필요 (UNKNOWN)';
}

function toPublicItem(row) {
  return {
    id: row.poi_id,
    name: row.poi_name,
    type: row.poi_type,
    floor: row.floor_info || '',
    description: row.description || '',
    wheelchairAccessStatus: row.wheelchair_access_status || 'UNKNOWN',
    latitude: Number(row.latitude),
    longitude: Number(row.longitude),
  };
}

function normalize(value) {
  return String(value || '').replace(/한양여자대학교|한양여대/g, '').replace(/[\s_()\-]/g, '').toLowerCase();
}

module.exports = { buildAgentResponse, detectIntent, extractBuildingWords };
