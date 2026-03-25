from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


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

    model_config = ConfigDict(from_attributes=True)
