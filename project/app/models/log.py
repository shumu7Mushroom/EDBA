from app.models.base import db
from datetime import datetime, timedelta

def beijing_now():
    return datetime.utcnow() + timedelta(hours=8)

class AccessLog(db.Model):
    __tablename__ = 'access_logs'

    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.String(100))            # 用户名或邮箱
    role = db.Column(db.String(50))             # ✅ 用户角色（如 student / teacher / admin / convener）
    organization = db.Column(db.String(100))    # ✅ 所属组织（如 CST / EDBA 等）
    url = db.Column(db.String(200))             # 被访问的 URL
    action = db.Column(db.String(200))          # 操作描述
    target = db.Column(db.String(200))          # ✅ 操作目标（如“论文 ID:10”、“学生 3”）
    timestamp = db.Column(db.DateTime, default=beijing_now)  # 时间戳
    ip = db.Column(db.String(50))               # IP 地址

    def jsonstr(self):
        return {
            "id": self.id,
            "user": self.user,
            "role": self.role,
            "organization": self.organization,
            "url": self.url,
            "action": self.action,
            "target": self.target,
            "timestamp": self.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            "ip": self.ip
        }
