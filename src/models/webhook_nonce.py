from sqlalchemy import Column, DateTime, Integer, String, UniqueConstraint, func
from models.base import Base


class WebhookNonce(Base):
    __tablename__ = "webhook_nonce"

    id = Column(Integer, primary_key=True)
    nonce = Column(String(255), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (UniqueConstraint("nonce"),)
