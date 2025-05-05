#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
中间件包初始化
"""

from .request_id import RequestIdMiddleware

__all__ = ['RequestIdMiddleware'] 