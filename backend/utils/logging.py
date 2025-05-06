import os
import sys
import logging
import time
from datetime import datetime
from pathlib import Path
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler

from backend.core.config import settings


# 日志级别映射
LOG_LEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL
}

# 默认日志级别
DEFAULT_LOG_LEVEL = "info"

# 默认日志格式
DEFAULT_LOG_FORMAT = "%(asctime)s [%(levelname)s] [%(process)d] [%(threadName)s] [%(filename)s:%(lineno)d] - %(message)s"

# 默认时间格式（北京时间）
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# 默认日志目录
DEFAULT_LOG_DIR = "logs"

# 默认日志文件大小和备份数量
DEFAULT_MAX_BYTES = 10 * 1024 * 1024  # 10MB
DEFAULT_BACKUP_COUNT = 30


class Logger:
    """
    统一日志管理类
    """
    
    def __init__(
        self, 
        name: str = "app", 
        level: str = DEFAULT_LOG_LEVEL,
        log_dir: str = DEFAULT_LOG_DIR,
        log_file: str = None,
        file_level: str = DEFAULT_LOG_LEVEL,
        console_level: str = DEFAULT_LOG_LEVEL,
        backup_count: int = DEFAULT_BACKUP_COUNT,
        max_bytes: int = DEFAULT_MAX_BYTES,
        log_format: str = DEFAULT_LOG_FORMAT,
        date_format: str = DEFAULT_DATE_FORMAT,
        console: bool = True,
        file: bool = True,
        log_rotation: str = "size"  # "size" 或 "time"
    ):
        """
        初始化日志记录器
        
        Args:
            name: 日志记录器名称
            level: 总体日志级别
            log_dir: 日志文件目录
            log_file: 日志文件名(如果为None，则使用name.log)
            file_level: 文件日志级别
            console_level: 控制台日志级别
            backup_count: 备份文件数量
            max_bytes: 单个日志文件最大字节数
            log_format: 日志格式
            date_format: 日期格式
            console: 是否输出到控制台
            file: 是否输出到文件
            log_rotation: 日志轮转方式，"size" 或 "time"
        """
        self.name = name
        self.log_dir = log_dir
        self.log_file = log_file or f"{name}.log"
        self.level = LOG_LEVELS.get(level.lower(), logging.INFO)
        self.file_level = LOG_LEVELS.get(file_level.lower(), logging.INFO)
        self.console_level = LOG_LEVELS.get(console_level.lower(), logging.INFO)
        self.backup_count = backup_count
        self.max_bytes = max_bytes
        self.log_format = log_format
        self.date_format = date_format
        self.console = console
        self.file = file
        self.log_rotation = log_rotation
        
        # 创建日志记录器
        self.logger = logging.getLogger(name)
        self.logger.setLevel(self.level)
        self.logger.propagate = False  # 避免日志重复
        
        # 清除已有的处理器
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # 创建日志格式器
        formatter = logging.Formatter(
            fmt=self.log_format,
            datefmt=self.date_format
        )
        
        # 添加控制台处理器
        if self.console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(self.console_level)
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
        
        # 添加文件处理器
        if self.file:
            file_handler = self.create_file_handler()
            self.logger.addHandler(file_handler)
            
            # 错误日志单独存储
            error_handler = self.create_error_handler()
            self.logger.addHandler(error_handler)

    def create_file_handler(self):
        """
        创建文件处理器
        
        Returns:
            文件处理器
        """
        # 确保日志目录存在
        log_dir_path = Path(self.log_dir)
        log_dir_path.mkdir(parents=True, exist_ok=True)
        
        # 创建日志文件路径
        log_file_path = log_dir_path / self.log_file
        
        # 确保日志文件存在
        if not log_file_path.exists():
            log_file_path.touch()
        
        try:
            # 创建按大小和时间轮转的日志处理器
            # 每天轮转，保留30天
            if self.log_rotation == "size":
                file_handler = RotatingFileHandler(
                    filename=str(log_file_path),
                    maxBytes=self.max_bytes,
                    backupCount=self.backup_count,
                    encoding="utf-8"
                )
            else:
                file_handler = TimedRotatingFileHandler(
                    filename=str(log_file_path),
                    when="midnight",
                    interval=1,
                    backupCount=self.backup_count,
                    encoding="utf-8"
                )
            
            file_handler.setLevel(self.file_level)
            file_handler.setFormatter(logging.Formatter(
                fmt=self.log_format,
                datefmt=self.date_format
            ))
            
            return file_handler
        except Exception as e:
            print(f"创建文件处理器失败: {str(e)}")
            raise
            
    def create_error_handler(self):
        """
        创建错误日志处理器，专门记录ERROR及以上级别的日志
        
        Returns:
            错误日志处理器
        """
        # 确保日志目录存在
        log_dir_path = Path(self.log_dir)
        log_dir_path.mkdir(parents=True, exist_ok=True)
        
        # 创建错误日志文件路径
        error_log_file = f"{self.name}.error.log"
        error_log_file_path = log_dir_path / error_log_file
        
        # 确保日志文件存在
        if not error_log_file_path.exists():
            error_log_file_path.touch()
            
        try:
            # 创建错误日志处理器
            if self.log_rotation == "size":
                error_handler = RotatingFileHandler(
                    filename=str(error_log_file_path),
                    maxBytes=self.max_bytes,
                    backupCount=self.backup_count,
                    encoding="utf-8"
                )
            else:
                error_handler = TimedRotatingFileHandler(
                    filename=str(error_log_file_path),
                    when="midnight",
                    interval=1,
                    backupCount=self.backup_count,
                    encoding="utf-8"
                )
                
            error_handler.setLevel(logging.ERROR)
            error_handler.setFormatter(logging.Formatter(
                fmt=self.log_format,
                datefmt=self.date_format
            ))
            
            return error_handler
        except Exception as e:
            print(f"创建错误日志处理器失败: {str(e)}")
            raise

    def get_logger(self):
        """获取日志记录器"""
        return self.logger


# 创建默认日志记录器
def get_logger(name: str = "app"):
    """
    获取日志记录器
    
    Args:
        name: 日志记录器名称
        
    Returns:
        日志记录器
    """
    log_level = os.getenv("LOG_LEVEL", DEFAULT_LOG_LEVEL)
    console_level = os.getenv("CONSOLE_LOG_LEVEL", log_level)
    file_level = os.getenv("FILE_LOG_LEVEL", log_level)
    log_rotation = os.getenv("LOG_ROTATION", "size")  # 默认按大小轮转
    
    # 获取日志文件大小和备份数量
    try:
        max_bytes = int(os.getenv("LOG_MAX_BYTES", str(DEFAULT_MAX_BYTES)))
    except (ValueError, TypeError):
        max_bytes = DEFAULT_MAX_BYTES
        
    try:
        backup_count = int(os.getenv("LOG_BACKUP_COUNT", str(DEFAULT_BACKUP_COUNT)))
    except (ValueError, TypeError):
        backup_count = DEFAULT_BACKUP_COUNT
    
    # 根据环境变量获取日志记录器配置
    logger = Logger(
        name=name,
        level=log_level,
        console_level=console_level,
        file_level=file_level,
        log_dir=os.getenv("LOG_DIR", DEFAULT_LOG_DIR),
        log_rotation=log_rotation,
        max_bytes=max_bytes,
        backup_count=backup_count
    ).get_logger()
    
    return logger


# 应用程序日志记录器
app_logger = get_logger("app")
api_logger = get_logger("api")
db_logger = get_logger("db")
auth_logger = get_logger("auth") 