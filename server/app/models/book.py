from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base
from app.db.types import UTCDateTime, utc_now

class Book(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    author = Column(String(128), nullable=True)
    cover_url = Column(String(1024), nullable=True)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(1024), nullable=False)
    
    # imported, processing, ready, limited, failed
    status = Column(String(32), default="imported", nullable=False) 
    status_detail = Column(Text, nullable=True)
    
    # 绑定的伴读好友
    ai_friend_id = Column(Integer, ForeignKey("friends.id"), nullable=True)
    
    # 阅读进度记录定位
    reading_location = Column(String(255), nullable=True)
    
    create_time = Column(UTCDateTime, default=utc_now, nullable=False)
    update_time = Column(UTCDateTime, default=utc_now, onupdate=utc_now, nullable=False)
    deleted = Column(Boolean, default=False, nullable=False)

    # 关联关系
    friend = relationship("Friend")
