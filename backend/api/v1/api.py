from fastapi import APIRouter

from backend.api.v1 import auth, users, profile, notes, chat, agent, tools

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["认证"])
api_router.include_router(users.router, prefix="/users", tags=["用户"])
api_router.include_router(profile.router, prefix="/profile", tags=["个人档案"])
api_router.include_router(notes.router, prefix="/notes", tags=["笔记"])
api_router.include_router(chat.router, prefix="/chat", tags=["聊天"])
api_router.include_router(agent.router, prefix="/agent", tags=["Agent"])
api_router.include_router(tools.router, prefix="/tools", tags=["工具"]) 