// src/routes/ingest.js
import { Router } from 'express';
import { config } from '../config.js';

const router = Router();

router.post('/', async (req, res) => {
  const { candidate_id, emails } = req.body;

  if (!candidate_id || candidate_id !== config.candidateId) {
    return res.status(400).json({ error: 'invalid_candidate_id' });
  }
  if (!Array.isArray(emails) || emails.length === 0) {
    return res.status(400).json({ error: 'emails must be a non-empty array' });
  }
  if (emails.length > 100) {
    return res.status(400).json({ error: 'batch size exceeds limit of 100' });
  }

  // Phase 2 fills the actual logic here
  return res.status(200).json({
    processed: 0,
    tasks_created: 0,
    tasks_updated: 0,
    skipped: 0,
    errors: [],
    message: 'Phase 2 classifier not yet wired — stub response',
  });
});

export default router;
