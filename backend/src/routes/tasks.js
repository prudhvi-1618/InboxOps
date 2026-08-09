// src/routes/tasks.js
import { Router } from 'express';
import { config } from '../config.js';

const router = Router();

router.get('/', async (req, res) => {
  try {
    const url = new URL(`${config.taskApiBase}/tasks`);
    url.searchParams.set('candidate_id', config.candidateId);
    if (req.query.thread_id) url.searchParams.set('thread_id', req.query.thread_id);
    if (req.query.assignee_id) url.searchParams.set('assignee_id', req.query.assignee_id);
    if (req.query.source_email_id) url.searchParams.set('source_email_id', req.query.source_email_id);

    const upstream = await fetch(url.toString());
    const data = await upstream.json();
    return res.status(upstream.status).json(data);
  } catch (err) {
    return res.status(502).json({ error: 'upstream_task_api_unavailable', detail: err.message });
  }
});

export default router;
