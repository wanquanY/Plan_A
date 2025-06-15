"""
MCP传输层实现

支持多种传输协议：
- stdio: 标准输入输出传输
- SSE: Server-Sent Events传输
"""

import asyncio
import json
import subprocess
import sys
from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Dict, Optional, Union, Callable
import httpx
from ..schemas.protocol import MCPMessage, MCPRequest, MCPResponse, MCPNotification
from ..schemas.exceptions import MCPConnectionError, MCPTimeoutError, MCPParseError
from backend.utils.logging import app_logger


class Transport(ABC):
    """传输层基类"""
    
    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout
        self.connected = False
        
    @abstractmethod
    async def connect(self) -> None:
        """建立连接"""
        pass
        
    @abstractmethod
    async def disconnect(self) -> None:
        """断开连接"""
        pass
        
    @abstractmethod
    async def send(self, message: Union[MCPRequest, MCPResponse, MCPNotification]) -> None:
        """发送消息"""
        pass
        
    @abstractmethod
    async def receive(self) -> AsyncIterator[Union[MCPRequest, MCPResponse, MCPNotification]]:
        """接收消息"""
        pass


class StdioTransport(Transport):
    """标准输入输出传输"""
    
    def __init__(self, command: str, args: list = None, timeout: float = 30.0, env: dict = None, **kwargs):
        super().__init__(timeout)
        self.command = command
        self.args = args or []
        self.env = env or {}
        self.process: Optional[subprocess.Popen] = None
        self._reader_task: Optional[asyncio.Task] = None
        self._message_queue = asyncio.Queue()
        
    async def connect(self) -> None:
        """启动子进程并建立连接"""
        try:
            app_logger.info(f"启动MCP服务器进程: {self.command} {' '.join(self.args)}")
            
            # 准备环境变量
            import os
            process_env = os.environ.copy()
            if self.env:
                process_env.update(self.env)
                app_logger.info(f"设置环境变量: {list(self.env.keys())}")
            
            self.process = await asyncio.create_subprocess_exec(
                self.command,
                *self.args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=process_env
            )
            
            # 启动读取任务
            self._reader_task = asyncio.create_task(self._read_messages())
            self.connected = True
            app_logger.info("MCP服务器连接成功")
            
        except Exception as e:
            app_logger.error(f"启动MCP服务器失败: {e}")
            raise MCPConnectionError(f"无法启动MCP服务器: {e}")
    
    async def disconnect(self) -> None:
        """断开连接并终止子进程"""
        if self._reader_task:
            self._reader_task.cancel()
            try:
                await self._reader_task
            except asyncio.CancelledError:
                pass
                
        if self.process:
            try:
                self.process.terminate()
                await asyncio.wait_for(self.process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self.process.kill()
                await self.process.wait()
            except Exception as e:
                app_logger.warning(f"终止MCP服务器进程时出错: {e}")
                
        self.connected = False
        app_logger.info("MCP服务器连接已断开")
    
    async def send(self, message: Union[MCPRequest, MCPResponse, MCPNotification]) -> None:
        """发送消息到子进程"""
        if not self.process or not self.connected:
            raise MCPConnectionError("未连接到MCP服务器")
            
        try:
            message_json = message.model_dump_json() + "\n"
            app_logger.info(f"发送MCP消息: {message_json.strip()}")
            
            if self.process.stdin:
                self.process.stdin.write(message_json.encode())
                await self.process.stdin.drain()
                app_logger.info("MCP消息发送成功")
            else:
                raise MCPConnectionError("进程stdin不可用")
                
        except Exception as e:
            app_logger.error(f"发送MCP消息失败: {e}")
            raise MCPConnectionError(f"发送消息失败: {e}")
    
    async def receive(self) -> AsyncIterator[Union[MCPRequest, MCPResponse, MCPNotification]]:
        """接收消息"""
        while self.connected:
            try:
                # 使用较短的超时时间，避免长时间阻塞
                message = await asyncio.wait_for(
                    self._message_queue.get(),
                    timeout=5.0  # 5秒超时，避免长时间阻塞
                )
                app_logger.debug(f"接收到MCP消息: {type(message).__name__}")
                yield message
            except asyncio.TimeoutError:
                # 静默处理超时，不打印警告（这是正常的空闲状态）
                continue
            except Exception as e:
                app_logger.error(f"接收MCP消息失败: {e}")
                break
    
    async def _read_messages(self) -> None:
        """从子进程读取消息"""
        if not self.process or not self.process.stdout:
            return
            
        try:
            app_logger.debug("开始读取MCP消息流")
            while self.connected and self.process.returncode is None:
                line = await self.process.stdout.readline()
                if not line:
                    app_logger.debug("MCP消息流结束")
                    break
                    
                try:
                    line_str = line.decode().strip()
                    if not line_str:
                        continue
                        
                    app_logger.info(f"接收到原始MCP消息: {line_str}")
                    
                    data = json.loads(line_str)
                    message = self._parse_message(data)
                    app_logger.info(f"解析MCP消息成功: {type(message).__name__}")
                    await self._message_queue.put(message)
                    
                except json.JSONDecodeError as e:
                    app_logger.error(f"解析MCP消息JSON失败: {e}, 消息: {line_str}")
                    continue
                except Exception as e:
                    app_logger.error(f"处理MCP消息失败: {e}")
                    continue
                    
        except Exception as e:
            app_logger.error(f"读取MCP消息流失败: {e}")
        finally:
            app_logger.debug("MCP消息读取结束")
            self.connected = False
    
    def _parse_message(self, data: Dict[str, Any]) -> Union[MCPRequest, MCPResponse, MCPNotification]:
        """解析消息"""
        try:
            if "id" in data:
                if "method" in data:
                    # Request
                    return MCPRequest(**data)
                else:
                    # Response
                    return MCPResponse(**data)
            elif "method" in data:
                # Notification
                return MCPNotification(**data)
            else:
                raise MCPParseError("无法识别的消息格式")
        except Exception as e:
            raise MCPParseError(f"解析消息失败: {e}")


class SSETransport(Transport):
    """Server-Sent Events传输"""
    
    def __init__(self, endpoint: str, timeout: float = 30.0, headers: Optional[Dict[str, str]] = None):
        super().__init__(timeout)
        self.endpoint = endpoint
        self.headers = headers or {}
        self.client: Optional[httpx.AsyncClient] = None
        self._event_stream: Optional[AsyncIterator] = None
        
    async def connect(self) -> None:
        """建立SSE连接"""
        try:
            app_logger.info(f"连接到MCP SSE端点: {self.endpoint}")
            
            self.client = httpx.AsyncClient(timeout=self.timeout)
            
            # 测试连接
            response = await self.client.get(
                self.endpoint + "/health",  # 假设有健康检查端点
                headers=self.headers
            )
            response.raise_for_status()
            
            self.connected = True
            app_logger.info("MCP SSE连接成功")
            
        except Exception as e:
            app_logger.error(f"连接MCP SSE失败: {e}")
            if self.client:
                await self.client.aclose()
            raise MCPConnectionError(f"无法连接到MCP SSE: {e}")
    
    async def disconnect(self) -> None:
        """断开SSE连接"""
        if self.client:
            await self.client.aclose()
        self.connected = False
        app_logger.info("MCP SSE连接已断开")
    
    async def send(self, message: Union[MCPRequest, MCPResponse, MCPNotification]) -> None:
        """通过HTTP POST发送消息"""
        if not self.client or not self.connected:
            raise MCPConnectionError("未连接到MCP服务器")
            
        try:
            message_data = message.model_dump()
            app_logger.debug(f"发送MCP SSE消息: {message_data}")
            
            response = await self.client.post(
                self.endpoint + "/message",
                json=message_data,
                headers=self.headers
            )
            response.raise_for_status()
            
        except Exception as e:
            app_logger.error(f"发送MCP SSE消息失败: {e}")
            raise MCPConnectionError(f"发送SSE消息失败: {e}")
    
    async def receive(self) -> AsyncIterator[Union[MCPRequest, MCPResponse, MCPNotification]]:
        """接收SSE消息"""
        if not self.client or not self.connected:
            raise MCPConnectionError("未连接到MCP服务器")
            
        try:
            async with self.client.stream(
                "GET",
                self.endpoint + "/events",
                headers={**self.headers, "Accept": "text/event-stream"}
            ) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        try:
                            data_str = line[6:]  # 移除 "data: " 前缀
                            if data_str.strip() == "[DONE]":
                                break
                                
                            data = json.loads(data_str)
                            message = self._parse_message(data)
                            yield message
                            
                        except json.JSONDecodeError as e:
                            app_logger.error(f"解析SSE数据失败: {e}")
                            continue
                        except Exception as e:
                            app_logger.error(f"处理SSE消息失败: {e}")
                            continue
                            
        except Exception as e:
            app_logger.error(f"接收SSE消息失败: {e}")
            raise MCPConnectionError(f"接收SSE消息失败: {e}")
    
    def _parse_message(self, data: Dict[str, Any]) -> Union[MCPRequest, MCPResponse, MCPNotification]:
        """解析消息"""
        try:
            if "id" in data:
                if "method" in data:
                    return MCPRequest(**data)
                else:
                    return MCPResponse(**data)
            elif "method" in data:
                return MCPNotification(**data)
            else:
                raise MCPParseError("无法识别的消息格式")
        except Exception as e:
            raise MCPParseError(f"解析消息失败: {e}")


def create_transport(transport_type: str, **config) -> Transport:
    """传输层工厂函数"""
    if transport_type == "stdio":
        return StdioTransport(**config)
    elif transport_type == "sse":
        return SSETransport(**config)
    else:
        raise ValueError(f"不支持的传输类型: {transport_type}") 