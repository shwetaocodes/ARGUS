"""add pipeline stage log table

Revision ID: d9e7ec7ebf14
Revises: 93ce877007b3
Create Date: 2026-08-19 14:38:52.422105

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'd9e7ec7ebf14'
down_revision: Union[str, Sequence[str], None] = '93ce877007b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    stagestatus = postgresql.ENUM('success', 'failed', 'skipped', name='stagestatus')
    stagestatus.create(bind, checkfirst=True)

    op.create_table('pipeline_stage_log',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('event_id', sa.Integer(), nullable=False),
    sa.Column('stage', sa.String(), nullable=False),
    sa.Column('status', postgresql.ENUM('success', 'failed', 'skipped', name='stagestatus', create_type=False), nullable=False),
    sa.Column('error_message', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['event_id'], ['events.id'], ),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('pipeline_stage_log')

    bind = op.get_bind()
    postgresql.ENUM(name='stagestatus').drop(bind, checkfirst=True)