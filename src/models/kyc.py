from sqlalchemy import CHAR, Column, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from models.base import Base
from models.customer import Customer


class KycRiskTier(Base):
    __tablename__ = "kyc_risk_tier"

    id = Column(Integer, primary_key=True)
    enumerator = Column(String(50), nullable=False)
    description = Column(String(255), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (UniqueConstraint("enumerator"),)


class KycAnalysis(Base):
    __tablename__ = "kyc_analysis"

    id = Column(Integer, primary_key=True)
    analysis_key = Column(CHAR(36), nullable=False)
    customer_id = Column(Integer, ForeignKey(Customer.id), nullable=False)
    risk_tier_id = Column(Integer, ForeignKey(KycRiskTier.id), nullable=False)
    score = Column(Integer, nullable=False)
    cnd_federal_status = Column(String(50), nullable=False)
    cnd_trabalhista_status = Column(String(50), nullable=False)
    cadsan_status = Column(String(50), nullable=False)
    flags = Column(JSONB, nullable=False)
    recommendation = Column(String(50), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (UniqueConstraint("analysis_key"),)

    customer = relationship("Customer", foreign_keys=[customer_id], lazy="selectin")
    risk_tier = relationship("KycRiskTier", foreign_keys=[risk_tier_id], lazy="selectin")
