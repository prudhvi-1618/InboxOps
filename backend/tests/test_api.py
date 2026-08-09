import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.infrastructure.database.connection import init_db


@pytest.fixture(autouse=True)
async def setup_db():
    await init_db()


@pytest.mark.asyncio
async def test_health_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "candidate_id" in data


@pytest.mark.asyncio
async def test_tasks_crud_flow():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Create a task
        payload = {
            "candidate_id": "nirujogiprudhvi@gmail.com",
            "source_email_id": "email_test_101",
            "thread_id": "th_test_101",
            "title": "Enterprise RFP for Cloud Hosting",
            "description": "Requirement for high security servers",
            "assignee_id": "u_aarti",
            "category": "enterprise_rfp",
            "priority": "high",
            "due_date": "2026-08-20",
            "deal_value_inr": 2500000,
            "company_name": "Acme Global",
            "confidence": 0.98,
        }
        res_create = await ac.post("/tasks", json=payload)
        assert res_create.status_code == 201
        created_task = res_create.json()
        assert "task_id" in created_task
        task_id = created_task["task_id"]
        assert created_task["title"] == payload["title"]
        assert created_task["deal_value_inr"] == 2500000

        # 2. Get task by ID
        res_get = await ac.get(f"/tasks/{task_id}")
        assert res_get.status_code == 200
        assert res_get.json()["task_id"] == task_id

        # 3. List tasks with filter
        res_list = await ac.get("/tasks", params={"candidate_id": "nirujogiprudhvi@gmail.com", "category": "enterprise_rfp"})
        assert res_list.status_code == 200
        tasks = res_list.json()
        assert isinstance(tasks, list)
        assert any(t["task_id"] == task_id for t in tasks)

        # 4. Patch task
        patch_payload = {
            "priority": "medium",
            "description": "Updated security requirements",
        }
        res_patch = await ac.patch(f"/tasks/{task_id}", json=patch_payload)
        assert res_patch.status_code == 200
        updated_task = res_patch.json()
        assert updated_task["priority"] == "medium"
        assert updated_task["description"] == "Updated security requirements"


@pytest.mark.asyncio
async def test_ingest_hygiene_skip():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        payload = {
            "candidate_id": "nirujogiprudhvi@gmail.com",
            "emails": [
                {
                    "email_id": "em_ooo_test",
                    "thread_id": "th_ooo_test",
                    "from_name": "Alice Bob",
                    "from_email": "alice@corp.com",
                    "subject": "Automatic reply: Out of office",
                    "body": "I am currently on annual leave until next Monday.",
                    "received_at": "2026-08-10T09:00:00Z",
                    "is_reply": False,
                    "message_index": 0,
                }
            ],
        }
        res = await ac.post("/ingest", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["processed"] == 1
        assert data["skipped"] == 1
        assert data["tasks_created"] == 0


@pytest.mark.asyncio
async def test_smoke_ooo_and_spam_skipping():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        payload = {
            "candidate_id": "nirujogiprudhvi@gmail.com",
            "emails": [
                {
                    "email_id": "em_ooo_01",
                    "thread_id": "th_ooo_01",
                    "subject": "Out of Office",
                    "body": "I am out of office until 14th August with limited access to email.",
                    "from_name": "Suresh",
                    "from_email": "s@company.com",
                    "received_at": "2026-08-08T10:00:00+05:30",
                    "is_reply": False,
                    "message_index": 0,
                },
                {
                    "email_id": "em_spam_01",
                    "thread_id": "th_spam_01",
                    "subject": "Grow your traffic",
                    "body": "We have helped 200+ SaaS companies 3x their organic traffic. Free audit — quick 15 min call?",
                    "from_name": "SEO Guy",
                    "from_email": "seo@agency.com",
                    "received_at": "2026-08-08T10:00:00+05:30",
                    "is_reply": False,
                    "message_index": 0,
                },
            ],
        }
        res = await ac.post("/ingest", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["processed"] == 2
        assert data["tasks_created"] == 0
        assert data["skipped"] == 2
        assert data["errors"] == []

        # Confirm no triage tasks created for OOO or spam
        tasks_res = await ac.get("/tasks", params={"candidate_id": "nirujogiprudhvi@gmail.com"})
        assert tasks_res.status_code == 200
        tasks = tasks_res.json()
        source_email_ids = [t["source_email_id"] for t in tasks]
        assert "em_ooo_01" not in source_email_ids
        assert "em_spam_01" not in source_email_ids


@pytest.mark.asyncio
async def test_ingest_idempotency():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        payload = {
            "candidate_id": "nirujogiprudhvi@gmail.com",
            "emails": [
                {
                    "email_id": "em_idempotent_test_01",
                    "thread_id": "th_idempotent_test_01",
                    "from_name": "Alice Bob",
                    "from_email": "alice@corp.com",
                    "subject": "Automatic reply: Out of office",
                    "body": "I am currently on annual leave until next Monday.",
                    "received_at": "2026-08-10T09:00:00Z",
                    "is_reply": False,
                    "message_index": 0,
                }
            ],
        }
        # First ingest
        res1 = await ac.post("/ingest", json=payload)
        assert res1.status_code == 200
        assert res1.json()["processed"] == 1

        # Second ingest of the exact same email_id
        res2 = await ac.post("/ingest", json=payload)
        assert res2.status_code == 200
        data2 = res2.json()
        assert data2["processed"] == 1
        assert data2["skipped"] == 1
        assert data2["tasks_created"] == 0


@pytest.mark.asyncio
async def test_stats_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/stats")
        assert res.status_code == 200
        stats = res.json()
        assert "totals" in stats
        assert "by_category" in stats
        assert "skip_reasons" in stats
