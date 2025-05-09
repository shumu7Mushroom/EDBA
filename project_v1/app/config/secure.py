# -*- coding: utf-8 -*-
# @Time    : 2019/4/28 23:35
# @Author  : 2010jing
# @Email   : 2010jing@gmail.com
# @File    : secure.py

# SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://kido:kido@bcrab.cn/kido?charset=utf8'
# SQLALCHEMY_TRACK_MODIFICATION = True

import os, sys

print("Loading secure.py from:", __file__)
UPLOAD_FOLDER = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        '..', '..', '..',
        'uploads'
    )
)
print("Configured UPLOAD_FOLDER =", UPLOAD_FOLDER)

SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:@localhost:3306/edba_db?charset=utf8mb4'
SQLALCHEMY_TRACK_MODIFICATIONS = False

MAIL_SERVER = 'smtp.qq.com'
MAIL_PORT = 465
MAIL_USE_SSL = True
MAIL_USERNAME = '1537142833@qq.com'
MAIL_PASSWORD = 'pyaklogvfcjsjafa'
MAIL_DEFAULT_SENDER = '1537142833@qq.com'
