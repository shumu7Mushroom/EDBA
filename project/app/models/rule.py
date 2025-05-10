from app.models.base import Base, db
from sqlalchemy import Column, Integer, String, Text

class Rule(Base):
    __tablename__ = 'rules'

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    filename = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'filename': self.filename,
            'description': self.description
        }
