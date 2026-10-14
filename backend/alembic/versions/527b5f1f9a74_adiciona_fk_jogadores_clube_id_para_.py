"""adiciona fk jogadores clube_id para clubes

Revision ID: 527b5f1f9a74
Revises: b7306ece8cc4
Create Date: 2026-10-14 07:26:19.659246

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '527b5f1f9a74'
down_revision: Union[str, Sequence[str], None] = 'b7306ece8cc4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_foreign_key(
        'fk_jogadores_clube_id_clubes', 'jogadores', 'clubes', ['clube_id'], ['id']
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('fk_jogadores_clube_id_clubes', 'jogadores', type_='foreignkey')
