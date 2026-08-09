// src/server.js
import 'dotenv/config';
import express from 'express';
import cors from 'cors';
import { config } from './config.js';
import db from './db.js';           // runs schema on import
import ingestRouter from './routes/ingest.js';
import tasksRouter  from './routes/tasks.js';
import statsRouter  from './routes/stats.js';
import chatRouter   from './routes/chat.js';

const app = express();

app.use(cors({
  origin: (origin, cb) => {
    // Allow Vercel preview URLs, localhost dev, and the known prod frontend
    const allowed = [
      /\.vercel\.app$/,
      /localhost/,
      /127\.0\.0\.1/,
    ];
    if (!origin || allowed.some(r => r.test(origin))) return cb(null, true);
    cb(new Error(`CORS: origin ${origin} not allowed`));
  },
  methods: ['GET', 'POST', 'PATCH', 'DELETE', 'OPTIONS'],
  allowedHeaders: ['Content-Type'],
}));

app.use(express.json({ limit: '10mb' }));

// Health check — grader smoke-tests this
app.get('/health', (req, res) => {
  res.json({
    status: 'ok',
    candidate_id: config.candidateId,
    timestamp: new Date().toISOString(),
  });
});

app.use('/ingest',     ingestRouter);
app.use('/api/tasks',  tasksRouter);
app.use('/api/stats',  statsRouter);
app.use('/api/chat',   chatRouter);

// 404 handler
app.use((req, res) => {
  res.status(404).json({ error: 'not_found', path: req.path });
});

// Global error handler — never let Express crash on unhandled errors
app.use((err, req, res, _next) => {
  console.error('[ERROR]', err.message);
  res.status(500).json({ error: 'internal_server_error', detail: err.message });
});

app.listen(config.port, () => {
  console.log(`[server] Running on port ${config.port}`);
  console.log(`[server] candidate_id: ${config.candidateId}`);
  console.log(`[server] task_api_base: ${config.taskApiBase}`);
  console.log(`[server] env: ${config.nodeEnv}`);
});
