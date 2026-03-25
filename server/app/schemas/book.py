from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class BookUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255, description="展示书名")
    author: Optional[str] = Field(None, max_length=128, description="原作者")
    ai_friend_id: Optional[int] = Field(None, description="绑定好友 ID，传 null 表示解绑")

    @field_validator("title", "author", mode="before")
    @classmethod
    def normalize_text_fields(cls, value):
        if value is None:
            return None
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value


class BookReadingLocationUpdate(BaseModel):
    reading_location: Optional[str] = Field(None, max_length=255, description="阅读定位值")
    progress: Optional[float] = Field(None, ge=0, le=1, description="阅读进度百分比（0-1），当前仅保留接口兼容")
    display_label: Optional[str] = Field(
        None,
        max_length=128,
        description="阅读进度展示文案，当前仅保留接口兼容",
    )

    @field_validator("reading_location", "display_label", mode="before")
    @classmethod
    def normalize_optional_text_fields(cls, value):
        if value is None:
            return None
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value


class Book(BaseModel):
    id: int
    title: str = Field(..., description="展示书名")
    author: Optional[str] = Field(None, description="原作者")
    cover_url: Optional[str] = Field(None, description="封面相对路径")
    file_name: str = Field(..., description="原始文件名")
    file_path: str = Field(..., description="图书文件相对路径")
    status: str = Field(..., description="图书状态")
    status_detail: Optional[str] = Field(None, description="状态说明")
    ai_friend_id: Optional[int] = Field(None, description="绑定好友 ID")
    reading_location: Optional[str] = Field(None, description="阅读定位值")
    create_time: datetime
    update_time: datetime
    deleted: bool
    file_size: Optional[int] = Field(None, description="文件大小（字节）")
    format_type: str = Field(..., description="格式类型")
    bound_friend_name: Optional[str] = Field(None, description="已绑定好友名称")
    bound_friend_avatar: Optional[str] = Field(None, description="已绑定好友头像")
    author_binding_status: str = Field(..., description="作者绑定状态：unbound/valid/invalid")
    author_binding_message: str = Field(..., description="作者绑定状态说明")

    model_config = ConfigDict(from_attributes=True)
