"""Add trees table

Revision ID: 66e56620891a
Revises: e176543c72a8
Create Date: 2023-05-05 22:48:14.628117

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '66e56620891a'
down_revision = 'e176543c72a8'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('trees',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('quota_media', sa.Integer(), nullable=True),
    sa.Column('quota_people', sa.Integer(), nullable=True),
    sa.Column('usage_media', sa.Integer(), nullable=True),
    sa.Column('usage_people', sa.Integer(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('trees')
    # ### end Alembic commands ###
