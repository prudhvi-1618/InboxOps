from fastapi import APIRouter
import random
import uuid
from datetime import datetime, timedelta, timezone

router = APIRouter()

_SENDERS = [
    ("Suresh Kulkarni", "s.kulkarni@meridiansteel.co.in"),
    ("Ankit Bose", "ankit@railyardlogistics.in"),
    ("Nandita Reddy", "nandita@saassummit.in"),
    ("Farhan Qureshi", "farhan@halcyonretail.com"),
    ("Priya Nair", "priya@techventures.in"),
    ("Accounts Team", "accounts@vantagecloudservices.com"),
    ("BHEL Procurement", "proc@bhel.in"),
    ("SEO Agency", "outreach@seogrowth.com"),
    ("B2B Weekly", "newsletter@b2bgrowth.com"),
    ("Zenith Cloud", "partnerships@zenithcloud.com"),
]

_TEMPLATES = [
    {
        "subject": "RFP - Enterprise Document Management System",
        "body": "Dear Team,\n\nPlease find our RFP for a document management system covering 4 plants and ~1,200 users. Indicative budget is Rs. 25 lakhs. Proposals must reach us by 12th August 2026.\n\nRegards,\n{name}",
        "is_reply": False,
    },
    {
        "subject": "Quick demo request",
        "body": "Hi,\n\nWe're a 30-person logistics startup in Pune. Can we get a demo sometime next week? Nothing urgent.\n\n— {name}",
        "is_reply": False,
    },
    {
        "subject": "Sponsorship confirmation needed",
        "body": "We're finalising sponsors for the India SaaS Summit. Gold tier is ₹4,00,000 and includes a keynote slot. We need confirmation by tomorrow EOD.\n\n— {name}",
        "is_reply": False,
    },
    {
        "subject": "Out of Office",
        "body": "I am out of office until 14th August with limited access to email. For urgent matters please contact my colleague.\n\n— {name}",
        "is_reply": False,
    },
    {
        "subject": "Invoice INV-2026-0331 overdue",
        "body": "Please find attached invoice INV-2026-0331 for Rs. 1,18,000 (incl. 18% GST) against PO-88214. Payment terms were Net 30 and this is now 12 days overdue.\n\n— {name}",
        "is_reply": False,
    },
    {
        "subject": "Reseller partnership enquiry",
        "body": "We're a Salesforce implementation partner across MEA with 40+ enterprise clients. We'd like to explore reselling your platform. Who handles partnerships?\n\n— {name}",
        "is_reply": False,
    },
    {
        "subject": "Grow your organic traffic",
        "body": "Hi, I noticed your website isn't ranking on page 1. We've helped 200+ SaaS companies 3x their organic traffic. Free audit — interested in a quick 15 min call?\n\n— {name}",
        "is_reply": False,
    },
    {
        "subject": "The B2B Growth Weekly — Issue #212",
        "body": "The B2B Growth Weekly — Issue #212. In this edition: why PLG is stalling, 5 pricing experiments that worked. [Unsubscribe]",
        "is_reply": False,
    },
    {
        "subject": "Tender Notice BHEL/PROC/2026/0847",
        "body": "Bharat Heavy Electricals Limited invites bids for analytics software licences. Estimated value: Rs. 6,50,000. Last date: 03-08-2026, 1700 hrs IST.",
        "is_reply": False,
    },
    {
        "subject": "Product enquiry for dealer network",
        "body": "Bhai, humko aapka product chahiye for our dealer network. Around 150 users honge. Budget approx 1.2 cr allocated hai for this FY. Thoda jaldi, board review 20th ko hai.",
        "is_reply": False,
    },
]


@router.post("/api/generate-samples")
async def generate_samples(body: dict):
    count = min(int(body.get("count", 100)), 100)
    base_time = datetime.now(timezone.utc) - timedelta(days=7)
    emails = []

    for i in range(count):
        template = _TEMPLATES[i % len(_TEMPLATES)]
        sender = _SENDERS[i % len(_SENDERS)]
        thread_id = f"th_{str(i // 2).zfill(4)}"  # pairs share thread_id
        email_id = f"em_{str(i + 1).zfill(5)}"
        received = (base_time + timedelta(hours=i * 2)).isoformat()
        is_reply = i % 2 == 1 and i > 0

        emails.append({
            "email_id": email_id,
            "thread_id": thread_id,
            "message_index": 1 if is_reply else 0,
            "from_name": sender[0],
            "from_email": sender[1],
            "to": "sales@company.com",
            "cc": [],
            "subject": ("Re: " if is_reply else "") + template["subject"],
            "body": template["body"].format(name=sender[0]),
            "received_at": received,
            "attachments": [],
            "is_reply": is_reply,
        })

    return emails
