from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector

from app.database import Base


class EmbeddingCache(Base):
    __tablename__ = "embedding_cache"

    id = Column(Integer, primary_key=True, index=True)
    text_hash = Column(String(64), unique=True, index=True, nullable=False)
    original_text = Column(Text, nullable=False)
    embedding = Column(Vector(1536), nullable=False)  # text-embedding-3-small 차원
    result = Column(Text, nullable=False)  # JSON 문자열로 저장
    created_at = Column(DateTime(timezone=True), server_default=func.now())