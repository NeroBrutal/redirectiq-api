"""initial empty migration

Revision ID: c89f4864817d
Revises:
Create Date: 2026-09-24 16:02:58.205280

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "c89f4864817d"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
