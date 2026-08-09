// src/routes/chat.js
import { Router } from 'express';

const router = Router();

router.post('/', async (req, res) => {
  const { query } = req.body;
  if (!query || typeof query !== 'string') {
    return res.status(400).json({ error: 'query is required' });
  }
  // Phase 5 fills the NL → SQL → Gemini grounding logic
  return res.status(200).json({
    answer: 'Chat endpoint not yet implemented (Phase 5).',
    supporting_data: {},
  });
});

export default router;
