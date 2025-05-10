from app.models.base import Base, db
from sqlalchemy import Column, Integer, String, Text, Boolean

class Thesis(Base):
    __tablename__ = 'thesis'

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False, unique=True)
    abstract = Column(Text, nullable=False)
    pdf_path = Column(String(255), nullable=True)  # local path or external URL
    price = Column(Integer, default=0)  # cost in quota units
    organization = Column(String(128), nullable=True)  # owning organization

    access_scope = Column(String(50), default='all')  # 'all', 'specific', 'self'
    access_type = Column(String(50), default='view')  # 'view', 'download'
    is_free = Column(Boolean, default=True)  # True = 免费，False = 按 price 收费
    specific_org = db.Column(db.String(128), nullable=True)
    uploader = Column(String(128), nullable=True) 
    is_check = Column(Boolean, default = False)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'abstract': self.abstract,
            'pdf_path': self.pdf_path,
            'price': self.price,
            'organization': self.organization,
            'access_scope': self.access_scope,
            'access_type': self.access_type,
            'is_free': self.is_free,
            'specific_org': self.specific_org, 
            'uploader': self.uploader,
            'is_check': self.is_check
        }