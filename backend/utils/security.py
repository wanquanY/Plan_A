import secrets
import string
from datetime import datetime, timedelta
from typing import Optional, Any, Union, Dict

from jose import jwt
from passlib.context import CryptContext

from backend.core.config import settings

# 密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """生成密码哈希"""
    return pwd_context.hash(password)


def create_access_token(
    subject: Union[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    """创建访问令牌"""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
    return encoded_jwt


def generate_random_string(length: int = 32) -> str:
    """生成随机字符串"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def mask_sensitive_value(value: str, mask_char: str = "*", visible_chars: int = 0) -> str:
    """
    将敏感值进行脱敏处理
    
    Args:
        value: 要脱敏的值
        mask_char: 用于遮盖的字符，默认为*
        visible_chars: 开头和结尾保留的可见字符数，默认为0（全部遮盖）
    
    Returns:
        脱敏后的字符串
    """
    if not value:
        return value
    
    if len(value) <= visible_chars * 2:
        return mask_char * 8  # 对于很短的值，直接返回8个mask字符
    
    if visible_chars > 0:
        prefix = value[:visible_chars]
        suffix = value[-visible_chars:]
        masked_length = max(8, len(value) - visible_chars * 2)
        return f"{prefix}{mask_char * masked_length}{suffix}"
    else:
        return mask_char * 10  # 默认返回10个mask字符


def mask_env_variables(env_dict: Optional[Dict[str, str]], sensitive_keys: Optional[set] = None) -> Dict[str, str]:
    """
    对环境变量字典中的敏感值进行脱敏
    
    Args:
        env_dict: 环境变量字典
        sensitive_keys: 敏感键名集合，如果为None则使用默认规则
    
    Returns:
        脱敏后的环境变量字典
    """
    if not env_dict:
        return {}
    
    # 默认的敏感键名模式（不区分大小写）
    if sensitive_keys is None:
        sensitive_keys = {
            'key', 'token', 'secret', 'password', 'pwd', 'pass', 'api_key', 
            'apikey', 'access_token', 'refresh_token', 'auth_token',
            'private_key', 'cert', 'certificate', 'credential', 'auth'
        }
    
    masked_env = {}
    for key, value in env_dict.items():
        key_lower = key.lower()
        
        # 检查键名是否包含敏感词
        is_sensitive = any(sensitive_word in key_lower for sensitive_word in sensitive_keys)
        
        if is_sensitive:
            masked_env[key] = mask_sensitive_value(value)
        else:
            masked_env[key] = value
    
    return masked_env


def mask_headers(headers_dict: Optional[Dict[str, str]]) -> Dict[str, str]:
    """
    对HTTP头部字典中的敏感值进行脱敏
    
    Args:
        headers_dict: HTTP头部字典
    
    Returns:
        脱敏后的头部字典
    """
    if not headers_dict:
        return {}
    
    # 敏感的头部键名（不区分大小写）
    sensitive_headers = {
        'authorization', 'x-api-key', 'x-auth-token', 'x-access-token',
        'cookie', 'x-csrf-token', 'x-requested-with', 'authentication'
    }
    
    masked_headers = {}
    for key, value in headers_dict.items():
        key_lower = key.lower()
        
        if key_lower in sensitive_headers:
            masked_headers[key] = mask_sensitive_value(value, visible_chars=4)
        else:
            masked_headers[key] = value
    
    return masked_headers


def mask_server_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    对服务器配置进行脱敏处理
    
    Args:
        config: 服务器配置字典
    
    Returns:
        脱敏后的配置字典
    """
    masked_config = config.copy()
    
    # 脱敏环境变量
    if 'env' in masked_config:
        masked_config['env'] = mask_env_variables(masked_config['env'])
    
    # 脱敏HTTP头部
    if 'headers' in masked_config:
        masked_config['headers'] = mask_headers(masked_config['headers'])
    
    # 脱敏API密钥
    if 'api_key' in masked_config and masked_config['api_key']:
        masked_config['api_key'] = mask_sensitive_value(masked_config['api_key'], visible_chars=4)
    
    return masked_config 