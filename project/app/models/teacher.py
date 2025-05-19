from sqlalchemy import Column, String, Integer, orm
from app.models.human import Human

class Teacher(Human):
    id = Column(Integer, primary_key=True, autoincrement=True)
    major = Column(String(50), nullable=False)

    organization = Column(String(100), default="")
    access_level = Column(Integer, default=3)
    thesis_quota = Column(Integer, default=100)
    from sqlalchemy import Boolean
    thesis_enabled = Column(Boolean, default=False)
    course_enabled = Column(Boolean, default=False)
    is_pay = Column(Boolean, default=False)  # 是否已缴费

    def __init__(self, name, age, major, email, password, organization="", access_level=3, thesis_quota=100, thesis_enabled=False, course_enabled=False, is_pay=False):
        super(Teacher,self).__init__(name, age, email, password)
        self.major = major
        self.organization = organization
        self.access_level = access_level
        self.thesis_quota = thesis_quota
        self.thesis_enabled = thesis_enabled
        self.course_enabled = course_enabled
        self.is_pay = is_pay