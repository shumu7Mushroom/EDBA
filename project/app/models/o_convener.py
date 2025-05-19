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

    # 新增：三项服务的积分费用
    identity_fee = Column(Integer, default=0)  # 身份认证
    score_fee = Column(Integer, default=0)     # 成绩查询
    thesis_fee = Column(Integer, default=0)    # 论文查询

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
            # 'is_pay': self.is_pay,  # 兼容老代码
            'identity_fee': self.identity_fee,
            'score_fee': self.score_fee,
            'thesis_fee': self.thesis_fee
        }
