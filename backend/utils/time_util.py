from datetime import datetime, timedelta, timezone
import pytz

# 北京时区
beijing_tz = pytz.timezone('Asia/Shanghai')

def get_beijing_now() -> datetime:
    """
    获取当前北京时间
    """
    # 确保返回的时间带有时区信息
    return datetime.now(beijing_tz)

def to_beijing_time(dt_or_timestamp=None):
    """
    将时间转换为北京时间
    :param dt_or_timestamp: datetime对象或时间戳（秒或毫秒）
    :return: 北京时间的datetime对象
    """
    # 如果没有提供时间，使用当前时间
    if dt_or_timestamp is None:
        return datetime.now(beijing_tz)
    
    # 如果是时间戳（秒）
    if isinstance(dt_or_timestamp, (int, float)) and dt_or_timestamp < 10000000000:
        dt = datetime.fromtimestamp(dt_or_timestamp, pytz.UTC)
        return dt.astimezone(beijing_tz)
    
    # 如果是时间戳（毫秒）
    elif isinstance(dt_or_timestamp, (int, float)):
        dt = datetime.fromtimestamp(dt_or_timestamp / 1000, pytz.UTC)
        return dt.astimezone(beijing_tz)
    
    # 如果是datetime但没有时区信息
    elif isinstance(dt_or_timestamp, datetime) and dt_or_timestamp.tzinfo is None:
        dt = pytz.UTC.localize(dt_or_timestamp)
        return dt.astimezone(beijing_tz)
    
    # 如果是有时区的datetime
    elif isinstance(dt_or_timestamp, datetime):
        return dt_or_timestamp.astimezone(beijing_tz)
    
    # 不支持的类型
    else:
        raise TypeError("不支持的时间类型，请提供datetime对象或时间戳")

def format_datetime(dt: datetime, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    格式化日期时间
    """
    if dt.tzinfo is None:
        dt = to_beijing_time(dt)
    return dt.strftime(fmt)

def get_unix_timestamp() -> int:
    """
    获取当前时间戳（秒）
    """
    return int(datetime.now().timestamp())

def get_unix_timestamp_ms() -> int:
    """
    获取当前时间戳（毫秒）
    """
    return int(datetime.now().timestamp() * 1000)

def timestamp_to_datetime(timestamp: int) -> datetime:
    """
    时间戳转为datetime（北京时间）
    """
    dt = datetime.fromtimestamp(timestamp)
    return to_beijing_time(dt)

def datetime_to_timestamp(dt: datetime) -> int:
    """
    datetime转为时间戳
    """
    if dt.tzinfo is None:
        dt = to_beijing_time(dt)
    return int(dt.timestamp()) 