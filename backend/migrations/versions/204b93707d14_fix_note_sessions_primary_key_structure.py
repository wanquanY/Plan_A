"""fix note_sessions primary key structure

Revision ID: 204b93707d14
Revises: 27c4c0f306f3
Create Date: 2025-06-03 11:13:33.088926

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '204b93707d14'
down_revision = '27c4c0f306f3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 删除现有的复合主键
    op.drop_constraint('note_sessions_pkey', 'note_sessions', type_='primary')
    
    # 创建序列
    op.execute('CREATE SEQUENCE note_sessions_id_seq')
    
    # 设置id列的默认值为序列的下一个值
    op.execute("ALTER TABLE note_sessions ALTER COLUMN id SET DEFAULT nextval('note_sessions_id_seq')")
    
    # 更新现有记录的id值
    op.execute("SELECT setval('note_sessions_id_seq', COALESCE(MAX(id), 1)) FROM note_sessions")
    op.execute("UPDATE note_sessions SET id = nextval('note_sessions_id_seq') WHERE id = 0 OR id IS NULL")
    
    # 创建新的主键
    op.create_primary_key('note_sessions_pkey', 'note_sessions', ['id'])
    
    # 设置is_primary的默认值
    op.execute("UPDATE note_sessions SET is_primary = false WHERE is_primary IS NULL")
    op.alter_column('note_sessions', 'is_primary', 
                   existing_type=sa.BOOLEAN(),
                   nullable=False,
                   server_default=sa.text('false'))


def downgrade() -> None:
    # 删除自增主键
    op.drop_constraint('note_sessions_pkey', 'note_sessions', type_='primary')
    
    # 移除序列
    op.execute("ALTER TABLE note_sessions ALTER COLUMN id DROP DEFAULT")
    op.execute('DROP SEQUENCE IF EXISTS note_sessions_id_seq')
    
    # 恢复复合主键
    op.create_primary_key('note_sessions_pkey', 'note_sessions', ['note_id', 'session_id'])
    
    # 恢复is_primary字段
    op.alter_column('note_sessions', 'is_primary',
                   existing_type=sa.BOOLEAN(),
                   nullable=True,
                   server_default=None) 