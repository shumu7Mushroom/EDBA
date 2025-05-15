from app.models.base import db
from sqlalchemy import Column, String, Integer, Text, DateTime
import datetime

class Course(db.Model):
    __tablename__ = 'courses'

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(20), nullable=False, unique=True)         # 课程代码
    name = Column(String(100), nullable=False)                     # 课程名称
    description = Column(Text, nullable=True)                      # 课程描述
    credits = Column(Integer, default=3)                           # 学分
    organization = Column(String(100), nullable=False)             # 所属组织/学院
    instructor = Column(String(100), nullable=True)                # 授课教师
    created_at = Column(DateTime, default=datetime.datetime.now)   # 创建时间
    updated_at = Column(DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now)  # 更新时间
    
    def to_dict(self):
        return {
            'id': self.id,
            'code': self.code,
            'name': self.name,
            'description': self.description,
            'credits': self.credits,
            'organization': self.organization,
            'instructor': self.instructor,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None
        }
