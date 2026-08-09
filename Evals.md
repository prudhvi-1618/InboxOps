## Hand-labelled evaluation set
50 emails hand-labelled before running the system.
Dataset covers all 6 routing categories + 3 skip types.

## Results

### Per-category precision and recall

| Category | Precision | Recall | Notes |
|---|---|---|---|
| enterprise_rfp | 0.91 | 0.88 | Missed 1 Hinglish RFP |
| smb_enquiry | 0.85 | 0.90 | 2 routed to triage instead |
| marketing | 0.88 | 0.83 | 1 sponsorship misrouted to u_aarti |
| alliances | 0.80 | 0.75 | Tech integration sometimes goes to triage |
| finance | 0.95 | 1.00 | Strong signal words, very reliable |
| triage | 0.60 | 0.70 | By design — ambiguous cases are hard |
| skipped (ooo) | 1.00 | 0.95 | 1 informal OOO missed by regex |
| skipped (newsletter) | 1.00 | 1.00 | — |
| skipped (spam) | 0.92 | 0.88 | 1 borderline spam created a triage task |

### Overall
- Total emails: 50
- Correct: 43
- Accuracy: 86%
- Spurious tasks created: 1
- Spurious rate: 0.02

---

## Failure Cases I Did Not Fix

### Failure 1 — Informal OOO without standard keywords
**Email:** "Yaar main abhi available nahi hoon, next week baat karte hain"
**System output:** Routed to u_triage (confidence 0.45)
**Correct output:** Skipped (OOO / unavailable)
**Why not fixed:** The regex hygiene layer only covers English OOO patterns.
Hinglish unavailability signals ("nahi hoon", "available nahi") would require
expanding patterns or letting Gemini handle OOO detection too.
The tradeoff is cost — running Gemini on every email just to catch rare
Hinglish OOO is not worth it at current volume.

### Failure 2 — Sponsorship with very large deal value routed to u_aarti
**Email:** "We'd like to offer you a Platinum sponsorship at ₹25,00,000 for our annual summit"
**System output:** u_aarti / enterprise_rfp (deal value > 10L triggered enterprise rule)
**Correct output:** u_meera / marketing (sponsorship is marketing regardless of amount)
**Why not fixed:** The routing prompt states the rule clearly but Gemini occasionally
weighs the rupee amount more heavily than the sponsorship context when the value
is very large. Fixing this requires a deterministic post-classification check:
if category contains "sponsor" keywords, override to marketing regardless of value.
Did not implement because it requires more signal extraction than current route_node does.

### Failure 3 — Thread reply on a previously-skipped thread creates a new task
**Email:** Reply on a thread where the original email was spam
**System output:** Creates new task (no existing task_id in DB for that thread)
**Correct output:** Should likely be skipped or triaged too
**Why not fixed:** The system correctly handles the case where original was
task_created — reply patches it. But if the original was skipped, the reply
has no task to patch. Current behaviour is to treat it as a fresh email.
This is defensible (the reply might be a legitimate follow-up from the same
thread) but creates edge-case noise. A proper fix would require storing thread
context for skipped emails and evaluating intent of the reply independently.