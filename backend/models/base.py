from datetime import datetime
from sqlalchemy import Column, Boolean, DateTime, text, func
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.expression import FunctionElement
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy import Integer
from backend.db.session import Base

# 自定义北京时间函数
class BeijingTimestamp(TIMESTAMP):
    def __init__(self, **kwargs):
        kwargs.setdefault('timezone', True)
        super().__init__(**kwargs)

    class Comparator(TIMESTAMP.Comparator):
        pass

    @property
    def python_type(self):
        return datetime

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return value

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return value


class BeijingTimestampText(FunctionElement):
    type = TIMESTAMP()
    name = 'get_beijing_timestamp'


@compiles(BeijingTimestampText)
def get_beijing_timestamp_default(element, compiler, **kw):
    # 直接获取Asia/Shanghai时区的时间戳
    return "timezone('Asia/Shanghai', now())"


class BaseModel(Base):
    """
    基础模型类，包含所有模型共有的字段
    """
    __abstract__ = True
    
    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(TIMESTAMP(timezone=True), default=BeijingTimestampText(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), default=BeijingTimestampText(), onupdate=BeijingTimestampText(), nullable=False)
    
    # 软删除字段
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    deleted_at = Column(TIMESTAMP(timezone=True), nullable=True)
    
    def soft_delete(self):
        """
        软删除记录
        """
        self.is_deleted = True
        self.deleted_at = BeijingTimestampText()
    
    def restore(self):
        """
        恢复软删除的记录
        """
        self.is_deleted = False
        self.deleted_at = None 