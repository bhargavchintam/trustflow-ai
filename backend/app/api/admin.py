"""POST /api/seed and POST /api/reset — demo controls."""
from fastapi import APIRouter, Depends

from app.api.identity import resolve_identity
from app.memory import service as memory
from app.models import Identity
from app.seed.bob_seed import seed_bob
from app.seed.tenant_isolation_seed import seed_tenant_isolation

router = APIRouter()


@router.post("/api/seed")
async def seed_endpoint():
    await seed_bob()
    await seed_tenant_isolation()
    return {"status": "seeded"}


@router.post("/api/reset")
async def reset_endpoint(identity: Identity = Depends(resolve_identity)):
    await memory.wipe_user(tenant_id=identity.tenant_id, user_id=identity.user_id)
    return {"status": "wiped", "tenant_id": identity.tenant_id, "user_id": identity.user_id}
