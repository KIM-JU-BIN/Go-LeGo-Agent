require('dotenv').config({ path: '.env' });

const express = require('express');
const path = require('path');
const mysql = require('mysql2/promise');
const { buildAgentResponse } = require('./services/accessibility-agent.service');

const app = express();
const PORT = Number(process.env.PORT || 3000);
const publicDir = path.join(__dirname, '..', 'public');

// 기존 AccessNavWeb과 동일한 MAPSERVICE_DB_* 우선 규칙을 사용합니다.
const db = mysql.createPool({
  host: process.env.MAPSERVICE_DB_HOST || process.env.DB_HOST || '127.0.0.1',
  port: Number(process.env.MAPSERVICE_DB_PORT || process.env.DB_PORT || 3306),
  user: process.env.MAPSERVICE_DB_USER || process.env.DB_USER || 'root',
  password:
    process.env.MAPSERVICE_DB_PASSWORD ||
    process.env.MAPSERVICE_DB_PASS ||
    process.env.DB_PASSWORD ||
    process.env.DB_PASS || '',
  database: process.env.MAPSERVICE_DB_NAME || process.env.DB_NAME || 'barrier_free_db',
  waitForConnections: true,
  connectionLimit: 5,
  queueLimit: 0,
});

app.use(express.json({ limit: '32kb' }));
app.use(express.static(publicDir));

app.get('/api/health', async (req, res) => {
  try {
    const [rows] = await db.execute('SELECT DATABASE() AS databaseName, 1 AS connected');
    res.json({ ok: true, database: rows[0].databaseName, connected: Boolean(rows[0].connected) });
  } catch (error) {
    console.error('DB health check failed:', error.message);
    res.status(503).json({
      ok: false,
      error: 'MySQL에 연결하지 못했습니다.',
      detail: error.code || error.message,
    });
  }
});

app.post('/api/agent/chat', async (req, res) => {
  const message = String(req.body?.message || '').trim();
  const mobilityType = normalizeMobilityType(req.body?.mobilityType);

  if (!message) return res.status(400).json({ ok: false, error: '질문을 입력해주세요.' });
  if (message.length > 200) return res.status(400).json({ ok: false, error: '질문은 200자 이내여야 합니다.' });

  try {
    const result = await buildAgentResponse(db, { message, mobilityType });
    res.json({ ok: true, mobilityType, ...result });
  } catch (error) {
    console.error('Agent request failed:', error);
    res.status(500).json({
      ok: false,
      error: '시설 정보를 조회하는 중 오류가 발생했습니다.',
      detail: error.code || error.message,
    });
  }
});

app.use('/api', (req, res) => res.status(404).json({ ok: false, error: '요청한 API를 찾을 수 없습니다.' }));
app.get('*', (req, res) => res.sendFile(path.join(publicDir, 'index.html')));

app.listen(PORT, () => {
  console.log('==========================================');
  console.log('Go-Lego Agent MVP server started');
  console.log(`Open: http://localhost:${PORT}`);
  console.log(`DB health check: http://localhost:${PORT}/api/health`);
  console.log('==========================================');
});

function normalizeMobilityType(value) {
  return ['walking', 'wheelchair', 'stroller', 'senior'].includes(value) ? value : 'walking';
}
