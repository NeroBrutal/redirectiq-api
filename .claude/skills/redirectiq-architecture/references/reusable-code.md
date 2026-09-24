# Reusable Code: helpers, dependencies, base classes

Plan.md Global Rule 10: no abstraction until it's needed at least twice. The patterns
below exist because they're needed by *every* feature from Phase 1 onward — that's the
bar for putting something here instead of in a feature folder.

## `core/dependencies.py` — shared FastAPI dependencies

Anything more than one router needs goes here, not copy-pasted per feature.

```python
# src/app/core/dependencies.py
from fastapi import Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import async_session_factory
from app.core.errors import UnauthorizedError


async def get_db() -> AsyncSession:
    async with async_session_factory() as session:
        yield session
        await session.commit()  # one commit per request, at the boundary


async def get_current_user(...):
    """Decodes the session/token. Raises UnauthorizedError, not HTTPException."""
    ...


async def get_current_org(user=Depends(get_current_user)):
    """The org comes from the authenticated user, never from a path/query param
    (Global Rule 1). If a route needs a *specific* org from the URL, it still must
    verify `user` belongs to it here, not trust the URL value."""
    ...


class Pagination:
    def __init__(self, limit: int = Query(50, ge=1, le=200), cursor: str | None = Query(None)):
        self.limit = limit
        self.cursor = cursor
```

## `core/schemas.py` — shared Pydantic mixins

```python
# src/app/core/schemas.py
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ORMBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class TimestampedOut(ORMBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
```

Feature response models extend `TimestampedOut` instead of redeclaring `id`/timestamps:

```python
class LinkOut(TimestampedOut):
    slug: str
    destination: str
```

## `core/repository.py` — generic base only where every repo repeats the same shape

Once two repositories need identical get/list-by-org boilerplate, extract it — not
before:

```python
# src/app/core/repository.py
from typing import Generic, TypeVar
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

ModelT = TypeVar("ModelT")


class OrgScopedRepository(Generic[ModelT]):
    model: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, *, org_id: str, id: str) -> ModelT | None:
        stmt = select(self.model).where(self.model.organization_id == org_id, self.model.id == id)
        return (await self._session.execute(stmt)).scalar_one_or_none()
```

Feature repositories inherit it and add only their feature-specific queries
(`slug_exists`, etc.) — the generic `get` doesn't need reimplementing every time.

## `core/validators.py` — reusable Pydantic validation

URL scheme/length/private-IP checks (Global Rule 4) are needed by `links` now and by
`webhooks` later (Phase 9) — write once as a reusable Pydantic `Annotated` type:

```python
# src/app/core/validators.py
from typing import Annotated
from pydantic import AfterValidator, HttpUrl


def _reject_private_targets(url: HttpUrl) -> HttpUrl:
    # resolve host, reject loopback/link-local/private ranges — SSRF guard
    ...
    return url


PublicHttpUrl = Annotated[HttpUrl, AfterValidator(_reject_private_targets)]
```

```python
class LinkCreate(BaseModel):
    destination: PublicHttpUrl
    slug: str | None = None
```

## Where things do NOT belong

- No `utils.py` grab-bag. A file named `utils.py` with unrelated functions is where
  reusable code goes to become unmaintainable — name modules by what they do
  (`validators.py`, `slugs.py`, `pagination.py`).
- Don't add a generic base class for something only one feature does. Duplicate it in
  that feature first; promote to `core/` the second time it's needed, per Global Rule 10.
- Cross-feature imports (e.g. `analytics` importing `links.repository` directly) are a
  sign the shared piece belongs in `core/` or that `analytics` should call `links`'
  *service*, not reach into its data layer.
