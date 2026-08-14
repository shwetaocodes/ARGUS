"""add language and topic to sources

Revision ID: 9fc604cede0b
Revises: 33b1dfd74231
Create Date: 2026-07-27 17:29:51.328124

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9fc604cede0b'
down_revision: Union[str, Sequence[str], None] = '33b1dfd74231'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    language_enum = sa.Enum('en', 'ur', 'zh', name='language')
    language_enum.create(op.get_bind(), checkfirst=True)

    op.add_column('sources', sa.Column('language', language_enum, nullable=True))
    op.add_column('sources', sa.Column('topic', sa.String(), nullable=True))

def downgrade():
    op.drop_column('sources', 'topic')
    op.drop_column('sources', 'language')

    language_enum = sa.Enum('en', 'ur', 'zh', name='language')
    language_enum.drop(op.get_bind(), checkfirst=True)