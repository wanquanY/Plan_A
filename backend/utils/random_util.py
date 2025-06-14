#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
随机数工具类
"""

import uuid
import random
import string
import time

class RandomUtil:
    """随机数工具类，提供各种随机数生成方法"""
    
    @staticmethod
    def generate_uuid():
        """生成UUID字符串，不含连字符"""
        return str(uuid.uuid4()).replace('-', '')
    
    @staticmethod
    def generate_random_str(length=8):
        """生成指定长度的随机字符串"""
        characters = string.ascii_letters + string.digits
        return ''.join(random.choice(characters) for _ in range(length))
    
    @staticmethod
    def generate_request_id():
        """生成请求ID，格式为：时间戳(毫秒)-随机字符串"""
        timestamp = int(time.time() * 1000)
        random_str = RandomUtil.generate_random_str(6)
        return f"{timestamp}-{random_str}"
    
    @staticmethod
    def generate_chat_id():
        """生成聊天会话ID，格式为：chat-随机字符串"""
        random_str = RandomUtil.generate_random_str(12)
        return f"chat-{random_str}"
    
    @staticmethod
    def generate_note_id():
        """生成笔记ID，格式为：note-随机字符串"""
        random_str = RandomUtil.generate_random_str(12)
        return f"note-{random_str}"
    
    @staticmethod
    def generate_agent_id():
        """生成Agent ID，格式为：agent-随机字符串"""
        random_str = RandomUtil.generate_random_str(12)
        return f"agent-{random_str}"
    
    @staticmethod
    def generate_user_id():
        """生成用户ID，格式为：user-随机字符串"""
        random_str = RandomUtil.generate_random_str(12)
        return f"user-{random_str}"
    
    @staticmethod
    def generate_message_id():
        """生成消息ID，格式为：msg-随机字符串"""
        random_str = RandomUtil.generate_random_str(12)
        return f"msg-{random_str}"
    
    @staticmethod
    def generate_tool_call_id():
        """生成工具调用ID，格式为：tool-随机字符串"""
        random_str = RandomUtil.generate_random_str(12)
        return f"tool-{random_str}"
    
    @staticmethod
    def generate_session_relation_id():
        """生成会话关联ID，格式为：rel-随机字符串"""
        random_str = RandomUtil.generate_random_str(12)
        return f"rel-{random_str}"
    
    @staticmethod
    def generate_random_number(min_val=1, max_val=100):
        """生成指定范围内的随机整数"""
        return random.randint(min_val, max_val) 