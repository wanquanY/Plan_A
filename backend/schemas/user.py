from pydantic import BaseModel, Field, validator
import re
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    username: str


class UserCreate(UserBase):
    username: str
    phone: str
    password: str
    password_confirm: str
    
    @validator("phone")
    def validate_phone(cls, v):
        if not re.match(r"^1[3-9]\d{9}$", v):
            raise ValueError("请输入有效的手机号码")
        return v
    
    @validator("password_confirm")
    def passwords_match(cls, v, values, **kwargs):
        if "password" in values and v != values["password"]:
            raise ValueError("两次输入的密码不匹配")
        return v


class UserUpdate(BaseModel):
    """用户信息更新模型"""
    username: Optional[str] = None
    phone: Optional[str] = None
    avatar_url: Optional[str] = None
    is_active: Optional[bool] = None
    
    @validator("phone")
    def validate_phone(cls, v):
        if v and not re.match(r"^1[3-9]\d{9}$", v):
            raise ValueError("请输入有效的手机号码")
        return v


class PasswordChange(BaseModel):
    """密码修改模型"""
    current_password: str
    new_password: str
    confirm_password: str
    
    @validator("confirm_password")
    def passwords_match(cls, v, values, **kwargs):
        if "new_password" in values and v != values["new_password"]:
            raise ValueError("两次输入的新密码不匹配")
        return v


class UserLogin(BaseModel):
    username_or_phone: str
    password: str


class UserInDB(UserBase):
    id: int
    username: str
    phone: str
    avatar_url: Optional[str] = None
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        orm_mode = True


class User(UserInDB):
    pass


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None 