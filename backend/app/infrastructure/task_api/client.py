import httpx
from app.core.config import get_settings
from app.core.exceptions import TaskAPIError
from app.core.logging import get_logger
from app.infrastructure.database.connection import get_db
from app.infrastructure.database.repository import EmailDecisionRepository

logger = get_logger(__name__)
settings = get_settings()


class TaskAPIClient:

    def __init__(self):
        self.base_url = settings.task_api_base_url.rstrip("/")
        self.candidate_id = settings.candidate_id_normalized
        self.timeout = settings.task_api_timeout_sec

    async def create_task(self, payload: dict) -> dict:
        payload["candidate_id"] = self.candidate_id
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(f"{self.base_url}/tasks", json=payload)
            if resp.status_code != 201:
                raise TaskAPIError(resp.status_code, f"Task API create failed: {resp.text}")
            return resp.json()
        except (httpx.ConnectError, httpx.ConnectTimeout, httpx.RequestError) as e:
            logger.debug(f"[task_client] HTTP connection failed ({e}), writing directly to DB")
            async with get_db() as db:
                repo = EmailDecisionRepository(db)
                return await repo.create_task(payload)

    async def update_task(self, task_id: str, payload: dict) -> dict:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.patch(f"{self.base_url}/tasks/{task_id}", json=payload)
            if resp.status_code != 200:
                raise TaskAPIError(resp.status_code, f"Task API update failed: {resp.text}")
            return resp.json()
        except (httpx.ConnectError, httpx.ConnectTimeout, httpx.RequestError) as e:
            logger.debug(f"[task_client] HTTP connection failed ({e}), updating directly in DB")
            async with get_db() as db:
                repo = EmailDecisionRepository(db)
                res = await repo.update_task(task_id, payload)
                if not res:
                    raise TaskAPIError(404, f"Task {task_id} not found")
                return res

    async def list_tasks(self, filters: dict = None) -> list[dict]:
        params = {"candidate_id": self.candidate_id}
        if filters:
            params.update(filters)
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(f"{self.base_url}/tasks", params=params)
            if resp.status_code != 200:
                raise TaskAPIError(resp.status_code, f"Task API list failed: {resp.text}")
            return resp.json()
        except (httpx.ConnectError, httpx.ConnectTimeout, httpx.RequestError) as e:
            logger.debug(f"[task_client] HTTP connection failed ({e}), listing directly from DB")
            async with get_db() as db:
                repo = EmailDecisionRepository(db)
                return await repo.list_tasks(filters)
