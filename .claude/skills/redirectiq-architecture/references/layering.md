# Feature Layering: router → service → repository

One direction of dependency only. Nothing skips a layer (a router never imports a
repository directly; a repository never imports a service).

## router.py — HTTP concerns only

- Declares the path, method, `response_model`, `status_code`, `operation_id`, `tags`.
- Resolves dependencies via `Depends` (db session, current org/user, the service itself).
- Calls exactly one service method and returns its result. No branching, no try/except,
  no direct DB or Redis calls.

```python
# src/app/links/router.py
from fastapi import APIRouter, Depends, status

from app.core.dependencies import get_current_org
from app.links.dependencies import get_link_service
from app.links.schemas import LinkCreate, LinkOut
from app.links.service import LinkService

router = APIRouter(prefix="/v1/links", tags=["links"])


@router.post(
    "", response_model=LinkOut, status_code=status.HTTP_201_CREATED, operation_id="create_link"
)
async def create_link(
    payload: LinkCreate,
    service: LinkService = Depends(get_link_service),
    org=Depends(get_current_org),
):
    return await service.create_link(
        org_id=org.id, slug=payload.slug, destination=str(payload.destination)
    )


@router.get("/{link_id}", response_model=LinkOut, operation_id="get_link")
async def get_link(
    link_id: str,
    service: LinkService = Depends(get_link_service),
    org=Depends(get_current_org),
):
    return await service.get_link(org_id=org.id, link_id=link_id)
```

## service.py — business logic

- Orchestrates one or more repositories (and other services).
- Owns every business rule: uniqueness checks, authorization decisions beyond
  "does this org own this row" (that part belongs in the repository's `WHERE`), rate
  limiting, cache invalidation.
- Raises domain exceptions from `exceptions.py` (see `error-handling.md`). Never raises
  `HTTPException` — that couples business logic to HTTP and bypasses the global handler.
- Takes its repository (or repositories) as constructor arguments so it's trivially
  unit-testable with a fake repository — no DB needed in service-level tests.

## repository.py — data access only

- Every query filters by `organization_id`, taken as a parameter — never reads it from
  anywhere else. This is the one place Global Rule 1 (multi-tenancy) actually gets
  enforced in code, so it must be consistent across every method.
- Returns ORM objects or `None`/`[]`. Never raises domain exceptions, never returns an
  HTTP status. "Not found" is `None`; the service decides what that means.
- No business rules here — not even "is this slug valid", which belongs in the service
  or the Pydantic schema.

```python
# src/app/links/repository.py
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.link import Link


class LinkRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, *, org_id: str, link_id: str) -> Link | None:
        stmt = select(Link).where(Link.organization_id == org_id, Link.id == link_id)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def slug_exists(self, *, org_id: str, slug: str) -> bool:
        stmt = select(Link.id).where(Link.organization_id == org_id, Link.slug == slug)
        return (await self._session.execute(stmt)).scalar_one_or_none() is not None

    async def create(self, *, org_id: str, slug: str, destination: str) -> Link:
        link = Link(organization_id=org_id, slug=slug, destination=destination)
        self._session.add(link)
        await self._session.flush()  # commit happens at the request boundary, not here
        return link
```

## schemas.py — this feature's Pydantic models

- Request models validate input (Global Rule 4): destination URL scheme/length/private-IP
  checks live here as validators, not in the service.
- Response models are explicit — never return an ORM object straight from a router;
  `response_model` does the shaping, but the model itself should list only the fields the
  frontend contract needs.
- Share cross-feature fields via mixins from `core/schemas.py` (see `reusable-code.md`),
  don't redeclare `id`/`created_at` in every feature.

## Wiring a service: `dependencies.py` per feature

```python
# src/app/links/dependencies.py
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.links.repository import LinkRepository
from app.links.service import LinkService


def get_link_service(session: AsyncSession = Depends(get_db)) -> LinkService:
    return LinkService(LinkRepository(session))
```

This is the pattern for every feature, so a new feature is always the same five files
plus this one `dependencies.py` — copy the `links` folder's shape when starting a new one.
