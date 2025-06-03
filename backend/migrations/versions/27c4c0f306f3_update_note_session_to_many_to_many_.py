"""update note session to many to many relationship

Revision ID: 27c4c0f306f3
Revises: 903a59e7596a
Create Date: 2025-06-03 11:10:13.696607

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '27c4c0f306f3'
down_revision = '903a59e7596a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 首先删除现有的主键约束
    op.drop_constraint('note_sessions_pkey', 'note_sessions', type_='primary')
    
    # 修改id列为自增主键
    op.alter_column('note_sessions', 'id',
                   existing_type=sa.INTEGER(),
                   nullable=False,
                   autoincrement=True)
    
    # 创建新的主键
    op.create_primary_key('note_sessions_pkey', 'note_sessions', ['id'])
    
    # 确保is_primary列有默认值
    op.alter_column('note_sessions', 'is_primary',
                   existing_type=sa.BOOLEAN(),
                   nullable=True,
                   server_default=sa.text('false'))


def downgrade() -> None:
    # 删除自增主键
    op.drop_constraint('note_sessions_pkey', 'note_sessions', type_='primary')
    
    # 恢复id列为普通整数
    op.alter_column('note_sessions', 'id',
                   existing_type=sa.INTEGER(),
                   nullable=False,
                   autoincrement=False)
    
    # 恢复复合主键
    op.create_primary_key('note_sessions_pkey', 'note_sessions', ['note_id', 'session_id'])
    
    # 移除is_primary默认值
    op.alter_column('note_sessions', 'is_primary',
                   existing_type=sa.BOOLEAN(),
                   nullable=True,
                   server_default=None) 