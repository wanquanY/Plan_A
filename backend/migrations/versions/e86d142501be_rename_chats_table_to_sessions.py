"""rename_chats_table_to_sessions

Revision ID: e86d142501be
Revises: f385d374b006
Create Date: 2025-05-03 10:58:34.587465

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'e86d142501be'
down_revision = 'f385d374b006'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### 重命名表而不是删除和新建，这样可以保留数据 ###
    
    # 重命名表
    op.rename_table('chats', 'sessions')
    
    # 重命名索引
    op.execute('ALTER INDEX ix_chats_id RENAME TO ix_sessions_id')
    op.execute('ALTER INDEX ix_chats_is_deleted RENAME TO ix_sessions_is_deleted')
    op.execute('ALTER INDEX ix_chats_user_id RENAME TO ix_sessions_user_id')
    
    # 更新外键约束
    op.drop_constraint('chat_messages_conversation_id_fkey', 'chat_messages', type_='foreignkey')
    op.create_foreign_key(None, 'chat_messages', 'sessions', ['conversation_id'], ['id'])


def downgrade() -> None:
    # ### 还原表名和索引 ###
    
    # 更新外键约束
    op.drop_constraint(None, 'chat_messages', type_='foreignkey')
    op.create_foreign_key('chat_messages_conversation_id_fkey', 'chat_messages', 'chats', ['conversation_id'], ['id'])
    
    # 重命名索引
    op.execute('ALTER INDEX ix_sessions_id RENAME TO ix_chats_id')
    op.execute('ALTER INDEX ix_sessions_is_deleted RENAME TO ix_chats_is_deleted')
    op.execute('ALTER INDEX ix_sessions_user_id RENAME TO ix_chats_user_id')
    
    # 重命名表
    op.rename_table('sessions', 'chats') 