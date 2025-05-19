from sqlalchemy import Column, String, Integer, orm
from app.models.human import Human

class Student(Human):
    id = Column(Integer, primary_key=True, autoincrement=True)
    college = Column(String(50), nullable=False)

    organization = Column(String(100), default="")
    access_level = Column(Integer, default=2)
    thesis_quota = Column(Integer, default=0)
    from sqlalchemy import Boolean
    thesis_enabled = Column(Boolean, default=False)
    course_enabled = Column(Boolean, default=False)
    is_pay = Column(Boolean, default=False)  # 是否已缴费


    def __init__(self, name, age, college, email, password, organization="", access_level=2, thesis_quota=0, thesis_enabled=False, course_enabled=False, is_pay=False):
        super(Student,self).__init__(name, age, email, password)
        self.college = college
        self.organization = organization
        self.access_level = access_level
        self.thesis_quota = thesis_quota
        self.thesis_enabled = thesis_enabled
        self.course_enabled = course_enabled
        self.is_pay = is_pay

    def jsonstr(self):

        jsondata = {
            'name': self.name,
            'age': self.age,
            'college': self.college,
            'email': self.email,
            'organization': self.organization,
            'access_level': self.access_level,
            'thesis_quota': self.thesis_quota,
            'thesis_enabled': self.thesis_enabled,
            'course_enabled': self.course_enabled,
            'is_pay': self.is_pay
        }
        return jsondata
