from sqlalchemy import Column, String, Boolean, Integer
from app.models.base import Base

class OConvener(Base):
    __tablename__ = 'o_convener'

    id = Column(Integer, primary_key=True, autoincrement=True)
    org_fullname = Column(String(128), nullable=False)
    org_shortname = Column(String(64), nullable=False)
    email = Column(String(128), unique=True, nullable=False)
    proof_path = Column(String(255), nullable=False)
    status_text = Column(String(20), default='pending')  # pending/approved/rejected
    code = Column(String(10))  # 存储验证码（临时）
    verified = Column(Boolean, default=False)  # 是否通过邮箱验证

    def jsonstr(self):
        return {
            'id': self.id,
            'org_fullname': self.org_fullname,
            'org_shortname': self.org_shortname,
            'email': self.email,
            'proof_path': self.proof_path,
            'status_text': self.status_text,
            'verified': self.verified,
            'create_time': self.create_time,
            'is_pay': self.is_pay
        }
