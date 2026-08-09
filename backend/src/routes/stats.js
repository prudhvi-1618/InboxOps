// src/routes/stats.js
import { Router } from 'express';
import db from '../db.js';

const router = Router();

router.get('/', (req, res) => {
  const totals = db.prepare(`
    SELECT
      COUNT(*) AS processed,
      SUM(CASE WHEN decision = 'task_created' THEN 1 ELSE 0 END) AS created,
      SUM(CASE WHEN decision = 'task_updated' THEN 1 ELSE 0 END) AS updated,
      SUM(CASE WHEN decision = 'skipped'      THEN 1 ELSE 0 END) AS skipped,
      SUM(CASE WHEN decision = 'error'        THEN 1 ELSE 0 END) AS errors
    FROM email_decisions
  `).get();

  const byCategory = db.prepare(`
    SELECT category, COUNT(*) as count
    FROM email_decisions
    WHERE decision IN ('task_created','task_updated')
    GROUP BY category
  `).all();

  const skipReasons = db.prepare(`
    SELECT skipped_reason, COUNT(*) as count
    FROM email_decisions
    WHERE decision = 'skipped'
    GROUP BY skipped_reason
  `).all();

  return res.json({ totals, byCategory, skipReasons });
});

export default router;
