"""
序列化工具模块

提供处理特殊类型（如datetime）的序列化功能。
"""

from datetime import datetime
from typing import Any, Dict, List, Union
from pydantic import BaseModel


def serialize_datetime(obj: Any) -> Any:
    """递归序列化对象中的datetime字段"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {key: serialize_datetime(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [serialize_datetime(item) for item in obj]
    else:
        return obj


def serialize_pydantic_model(model: BaseModel) -> Dict[str, Any]:
    """序列化Pydantic模型，处理datetime字段"""
    data = model.model_dump()
    return serialize_datetime(data)


def serialize_pydantic_models(models: List[BaseModel]) -> List[Dict[str, Any]]:
    """序列化Pydantic模型列表，处理datetime字段"""
    return [serialize_pydantic_model(model) for model in models] 