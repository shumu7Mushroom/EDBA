from flask import Flask, render_template, request, session, redirect, url_for, flash
from flask_mail import Mail
from flask_migrate import Migrate
from flask import Blueprint
import os
from app.controller import book, student, teacher, user, admin, oconvener, log, verify, home, senior_admin, t_admin, course, help

from app.models.base import db
from app.models.bank_config import BankConfig

mail = Mail()

# 定义注册蓝图方法
def register_blueprints(app):
    app.register_blueprint(book.bookBP,url_prefix='/book')
    app.register_blueprint(student.studentBP,url_prefix='/student')
    app.register_blueprint(teacher.teacherBP,url_prefix='/teacher')
    app.register_blueprint(user.userBP,url_prefix='/user')
    app.register_blueprint(admin.adminBP,url_prefix='/admin')
    app.register_blueprint(senior_admin.senioradminBP,url_prefix='/senioradmin')    
    app.register_blueprint(oconvener.oconvenerBP, url_prefix='/oconvener')
    app.register_blueprint(log.logBP, url_prefix='/log')    
    app.register_blueprint(verify.verifyBP, url_prefix='/verify')
    app.register_blueprint(home.mainBP,url_prefix='')
    app.register_blueprint(t_admin.tadminBP,url_prefix='/tadmin')
    app.register_blueprint(course.courseBP,url_prefix='/course')
    app.register_blueprint(help.helpBP, url_prefix='/help')
    app.register_blueprint(bankConfigBP, url_prefix='/bank_config')

# 注册插件(数据库关联)
def register_plugin(app):
    db.init_app(app)
    Migrate(app, db)
    mail.init_app(app)
    with app.app_context():
        db.create_all()

def register_filters(app):
    app.jinja_env.filters['basename'] = lambda path: os.path.basename(path)

def create_app():
    app = Flask(__name__)
    # app.config.from_object('app.config.setting') # 基本配置(setting.py) 
    app.config.from_object('app.config.secure') # 重要参数配置(secure.py)、

    # ✅ 添加 secret_key
    app.secret_key = 'a-very-secret-key'  # 可以随便写，正式项目应更安全
    
    register_filters(app)

    # 注册蓝图与app对象相关联
    register_blueprints(app)
    # 注册插件(数据库)与app对象相关联
    register_plugin(app)
    # 一定要记得返回app
    return app

# 定义银行配置蓝图
bankConfigBP = Blueprint('bank_config', __name__)

@bankConfigBP.route('/api', methods=['GET', 'POST'])
def bank_api_config():
    if session.get('user_role') != 'convener':
        return redirect(url_for('oconvener.login'))
        
    # 获取当前用户ID
    user_id = session.get('user_id')
    
    if request.method == 'POST':
        # 根据user_id查找现有配置
        config = BankConfig.query.filter_by(user_id=user_id).first()
        
        if not config:
            # 如果找不到对应配置，创建新配置
            config = BankConfig()
            config.user_id = user_id  # 设置user_id
        
        # 保存基本API配置
        config.base_url = request.form.get('base_url', '').strip()
        config.auth_path = request.form.get('auth_path', '').strip()
        config.transfer_path = request.form.get('transfer_path', '').strip()
        
        # 保存o-convener API配置
        config.bank_name = request.form.get('bank', '').strip()
        config.account_name = request.form.get('account_name', '').strip()
        config.bank_account = request.form.get('account_number', '').strip()
        config.bank_password = request.form.get('password', '').strip()
        
        # 保存输入模板到api_config
        config.api_config = {
            'input_template': {
                'bank': request.form.get('bank'),
                'account_name': request.form.get('account_name'),
                'account_number': request.form.get('account_number'),
                'password': request.form.get('password')
            }
        }
        
        try:
            db.session.add(config)
            db.session.commit()
            flash('银行 API 配置已添加/更新', 'success')
            return redirect(url_for('oconvener.pay_fee'))
        except Exception as e:
            db.session.rollback()
            print(f"Error saving config: {str(e)}")  # 添加调试日志
            flash(f'保存配置失败: {str(e)}', 'error')
    
    # 对于GET请求，尝试获取当前用户的现有配置
    config = BankConfig.query.filter_by(user_id=user_id).first()
    return render_template('bank_api_config.html', config=config)