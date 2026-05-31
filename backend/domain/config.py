"""
API 配置模型
"""
from pydantic import BaseModel
from typing import Optional, List, Literal


class LLMConfig(BaseModel):
    """LLM API configuration"""
    api_base: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    api_key: str = ""
    api_keys: List[str] = []
    model: str = "gemini-2.0-flash"
    # remove.bg config
    removebg_api_key: str = ""
    bg_removal_method: Literal["local", "removebg"] = "local"
    # Ciudad por defecto para el clima
    weather_location: str = "Madrid, Comunidad de Madrid, España"
    # Signo zodiacal del usuario
    zodiac_sign: str = ""


class LLMConfigUpdate(BaseModel):
    """更新 LLM 配置的请求体"""
    api_base: Optional[str] = None
    api_key: Optional[str] = None
    api_keys: Optional[List[str]] = None
    model: Optional[str] = None
    removebg_api_key: Optional[str] = None
    bg_removal_method: Optional[Literal["local", "removebg"]] = None
    weather_location: Optional[str] = None
    zodiac_sign: Optional[str] = None


class AvailableModel(BaseModel):
    """可用模型"""
    id: str
    name: str
    

class ModelListResponse(BaseModel):
    """模型列表响应"""
    models: List[AvailableModel]
