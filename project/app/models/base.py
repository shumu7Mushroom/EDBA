from datetime import datetime
from flask_sqlalchemy import SQLAlchemy as _SQLAlchemy, BaseQuery
from sqlalchemy import inspect, Column, Integer, SmallInteger, orm
from contextlib import contextmanager


class SQLAlchemy(_SQLAlchemy):

    @contextmanager
    def auto_commit(self):
        try:
            yield  # 上文执行后会返回继续往下执行
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise e

db = SQLAlchemy(query_class=BaseQuery)


class Base(db.Model):
    __abstract__ = True # 抽象模型，不会创建实体表，否则需要创建主键
    
    # 增加一个创建时间的属性,用于记录实例对象创建的时间
    create_time = Column('create_time', Integer)
    # default=1表示未删除，=0表示已删除
    status = Column(SmallInteger, default=1)

    def __init__(self, **kwargs):
        # 获取系统时间戳作为对象创建的时间
        super().__init__(**kwargs)
        self.create_time = int(datetime.now().timestamp())

    # 设置对象返回字典的值(value), 同样是所有实例通用的方法，所以放在Base类中
    def __getitem__(self, item):
        return getattr(self, item)

    # 设置列属性的方法(所有实例共有)
    def set_attrs(self, attrs_dict):
        for key, value in attrs_dict.items():
            if hasattr(self, key) and key != 'id':
                setattr(self, key, value)

    # 定义删除模型对象的方法
    def delete(self):
        self.status = 0
