from openai import OpenAI, AsyncOpenAI
from backend.core.config import settings
from backend.utils.logging import api_logger


class OpenAIClientService:
    """OpenAI客户端服务"""
    
    def __init__(self):
        self._client = None
        self._async_client = None
        self._initialize_clients()
    
    def _initialize_clients(self):
        """初始化OpenAI客户端"""
        # 获取配置并进行调整
        api_key = settings.OPENAI_API_KEY
        base_url = settings.OPENAI_BASE_URL
        model = settings.OPENAI_MODEL
        
        # 确保base_url以/v1结尾
        if base_url and not base_url.endswith('/v1'):
            base_url = base_url.rstrip() + '/v1'
            api_logger.info(f"修正后的BASE URL: {base_url}")
        
        # 打印OpenAI配置信息
        api_logger.info(f"OpenAI配置 - API KEY: {api_key[:5]}*****, BASE URL: {base_url}, 模型: {model}")
        
        # 配置OpenAI客户端
        self._client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )
        
        # 配置异步OpenAI客户端
        self._async_client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url
        )
        
        # 打印客户端信息
        api_logger.info(f"OpenAI客户端初始化完成 - 同步客户端: {self._client.base_url}, 异步客户端: {self._async_client.base_url}")
    
    @property
    def client(self) -> OpenAI:
        """获取同步OpenAI客户端"""
        return self._client
    
    @property
    def async_client(self) -> AsyncOpenAI:
        """获取异步OpenAI客户端"""
        return self._async_client
    
    @property
    def model(self) -> str:
        """获取默认模型"""
        return settings.OPENAI_MODEL


# 创建全局客户端服务实例
openai_client_service = OpenAIClientService() 