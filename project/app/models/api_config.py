from app.models.base import db
from sqlalchemy.dialects.mysql import JSON   # ✅

class APIConfig(db.Model):
    __tablename__ = 'api_config'

    id            = db.Column(db.Integer, primary_key=True)
    institution_id= db.Column(db.Integer, nullable=True)  # 先留着
    service_type  = db.Column(db.String(50), nullable=False)   # identity / score …
    base_url      = db.Column(db.String(255), nullable=False)
    path          = db.Column(db.String(255), nullable=False)
    method        = db.Column(db.String(10),  nullable=False, default='POST')
    input         = db.Column(JSON)   # 👈 请求模板
    output        = db.Column(JSON)   # 👈 返回模板（可选，用来做校验或文档）
    created_at    = db.Column(db.DateTime, server_default=db.func.now())

    # 移除唯一约束，支持多个API配置
