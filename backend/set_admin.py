#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
将指定用户设置为管理员
"""

import os
import sys

# 添加项目根目录到路径，确保可以导入模块
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.models.user import User
from backend.core.config import settings

# 创建数据库会话
engine = create_engine(settings.SQLALCHEMY_DATABASE_URI.replace("+asyncpg", ""))
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

def set_admin(username):
    """将指定用户设置为管理员"""
    try:
        # 查找用户
        user = db.query(User).filter(User.username == username).first()
        
        if not user:
            print(f"错误: 未找到用户 '{username}'")
            return False
        
        # 设置为管理员
        user.is_superuser = True
        db.commit()
        
        print(f"成功: 用户 '{username}' 已设置为管理员")
        return True
    except Exception as e:
        db.rollback()
        print(f"错误: 设置管理员失败 - {str(e)}")
        return False

def list_users():
    """列出所有用户"""
    try:
        users = db.query(User).all()
        print("\n所有用户:")
        print("-" * 60)
        print(f"{'ID':<5} {'用户名':<15} {'电话':<15} {'是否激活':<10} {'是否管理员':<10}")
        print("-" * 60)
        
        for user in users:
            print(f"{user.id:<5} {user.username:<15} {user.phone:<15} {'是' if user.is_active else '否':<10} {'是' if user.is_superuser else '否':<10}")
        
        print("-" * 60)
    except Exception as e:
        print(f"错误: 获取用户列表失败 - {str(e)}")

if __name__ == "__main__":
    # 列出所有用户
    list_users()
    
    # 检查命令行参数
    if len(sys.argv) < 2:
        print("\n用法: python set_admin.py <username>")
        print("例如: python set_admin.py admin")
        sys.exit(1)
    
    # 设置管理员
    username = sys.argv[1]
    set_admin(username)
    
    # 再次列出所有用户以验证更改
    list_users() 