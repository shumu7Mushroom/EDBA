from flask import Flask
from app.controller import book, student, teacher, user, admin, oconvener, log, verify, home
from flask_mail import Mail
from flask_migrate import Migrate

mail = Mail()

# 定义注册蓝图方法
def register_blueprints(app):
    app.register_blueprint(book.bookBP,url_prefix='/book')
    app.register_blueprint(student.studentBP,url_prefix='/student')
    app.register_blueprint(teacher.teacherBP,url_prefix='/teacher')
    app.register_blueprint(user.userBP,url_prefix='/user')
    app.register_blueprint(admin.adminBP,url_prefix='/admin')
    app.register_blueprint(oconvener.oconvenerBP, url_prefix='/oconvener')
    app.register_blueprint(log.logBP, url_prefix='/log')
    app.register_blueprint(verify.verifyBP, url_prefix='/verify')
    app.register_blueprint(home.mainBP,url_prefix='')


# 注册插件(数据库关联)
def register_plugin(app):
    from app.models.base import db
    db.init_app(app)
    # create_all要放到app上下文环境中使用
    Migrate(app, db)  # ✅ 注册 Migrate
    mail.init_app(app)  # ✅ 初始化 Mail
    with app.app_context():
        db.create_all()


def create_app():
    app = Flask(__name__)
    # app.config.from_object('app.config.setting') # 基本配置(setting.py) 
    app.config.from_object('app.config.secure') # 重要参数配置(secure.py)、

    # ✅ 添加 secret_key
    app.secret_key = 'a-very-secret-key'  # 可以随便写，正式项目应更安全

    # 注册蓝图与app对象相关联
    register_blueprints(app)
    # 注册插件(数据库)与app对象相关联
    register_plugin(app)
    # 一定要记得返回app
    return app