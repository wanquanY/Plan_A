from fastapi import APIRouter

from backend.api.v1.endpoints import auth, users, note, chat, agent, tools, tool_calls, mcp

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["认证"])
api_router.include_router(users.router, prefix="/users", tags=["用户"])
api_router.include_router(note.router, prefix="/note", tags=["笔记"])
api_router.include_router(chat.router, prefix="/chat", tags=["聊天"])
api_router.include_router(agent.router, prefix="/agent", tags=["Agent"])
api_router.include_router(tools.router, prefix="/tools", tags=["工具"])
api_router.include_router(tool_calls.router, prefix="/tool-calls", tags=["工具调用"])
api_router.include_router(mcp.router, prefix="/mcp", tags=["MCP"]) 