from app.models.base import db
from datetime import datetime

class AccessLog(db.Model):
    __tablename__ = 'access_logs'

    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.String(100))            # 用户名或邮箱
    url = db.Column(db.String(200))             # 被访问的 URL
    action = db.Column(db.String(200))          # 操作描述
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)  # 时间戳
    ip = db.Column(db.String(50))               # IP 地址

    def jsonstr(self):
        return {
            "id": self.id,
            "user": self.user,
            "url": self.url,
            "action": self.action,
            "timestamp": self.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            "ip": self.ip
        }