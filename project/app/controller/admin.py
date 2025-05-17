from app.models.bank_config import BankConfig
from flask import Blueprint, render_template, request, session, redirect, url_for, current_app, send_from_directory, flash
from app.models.E_admin import EAdmin
from app.models.Senior_E_Admin import SeniorEAdmin
from app.models.o_convener import OConvener
from app.models.rule import Rule
from app.models.base import db
from app.controller.log import log_access  # ✅ 添加日志记录函数
import os
from werkzeug.utils import secure_filename
from app.models.T_admin import TAdmin

adminBP = Blueprint('admin', __name__)
print("adminBP 路由已加载")


# E-Admin 设置银行账户和会费
@adminBP.route('/bank_config', methods=['GET', 'POST'])
def bank_config():
    if session.get('admin_role') != 'eadmin':
        return redirect(url_for('admin.dashboard'))
    config = BankConfig.query.first()
    msg = None
    if request.method == 'POST':
        bank_account = request.form['bank_account']
        fee = int(request.form['fee'])
        if not config:
            config = BankConfig(bank_account=bank_account, fee=fee)
            db.session.add(config)
        else:
            config.bank_account = bank_account
            config.fee = fee
        db.session.commit()
        msg = "银行账户和会费已更新。"
    return render_template('bank_config.html', config=config, msg=msg)

# 登录界面
@adminBP.route('/login', methods=['GET', 'POST'])
def admin_login():
    session.clear()  # ✅ 清除之前的 session
    if request.method == 'GET':
        return render_template('admin_login.html')
    
    email = request.form.get('email')
    password = request.form.get('password')
    role = request.form.get('role')

    if role == 'eadmin':
        admin = EAdmin.query.filter_by(email=email, _password=password).first()
    elif role == 'senior':
        admin = SeniorEAdmin.query.filter_by(email=email, _password=password).first()
    elif role == 'tadmin':
        admin = TAdmin.query.filter_by(email=email, _password=password).first()
    else:
        admin = None
    session['user_org'] = "admin"

    if admin:
        
        session['admin_id'] = admin.id
        session['admin_role'] = role
        session['admin_name'] = admin.name
        

        log_access(f"{role} 登录成功（ID: {admin.id}）")

        # 👇 分开跳转
        if role == 'eadmin':
            session['user_role'] = 'eadmin'
            return redirect(url_for('admin.dashboard'))
        elif role == 'senior':
            session['user_role'] = 'senior'
            return redirect(url_for('senioradmin.dashboard'))
        elif role == 'tadmin':
            session['user_role'] = 'tadmin'
            return redirect(url_for('tadmin.dashboard'))
    else:
        log_access(f"{role} 登录失败（email: {email}）")  # ✅ 记录登录失败
        return render_template('admin_login.html', error='Invalid credentials')


# 管理后台界面
@adminBP.route('/dashboard')
def dashboard():
    if 'admin_id' not in session:
        return redirect(url_for('admin.admin_login'))

    role = session.get('admin_role')
    conv_list = []
    rules = []  # ✅ 防止未定义

    if role == 'eadmin':
        conv_list = OConvener.query.filter_by(status_text='pending').all()
        rules = Rule.query.all()
    elif role == 'senior':
        conv_list = OConvener.query.filter_by(status_text='reviewed').all()

    log_access(f"访问管理员后台（角色: {role}）")
    return render_template('admin_dashboard.html', conv_list=conv_list, role=role, rules=rules)

@adminBP.route('/approve/<int:id>', methods=['POST'])
def approve(id):
    role = session.get('admin_role')
    convener = OConvener.query.get(id)
    if not convener:
        return redirect(url_for('admin.dashboard'))

    if role == 'eadmin':
        convener.status_text = 'reviewed'
        log_access(f"E-Admin 审核通过注册申请（O-Convener ID: {id}）")
    elif role == 'senior':
        convener.status_text = 'approved'
        log_access(f"Senior E-Admin 审核通过注册申请（O-Convener ID: {id}）")

    db.session.commit()
    return redirect(url_for('admin.dashboard'))


@adminBP.route('/admin/reject/<int:id>', methods=['POST'])
def reject(id):
    role = session.get('admin_role')
    convener = OConvener.query.get(id)
    if not convener:
        return redirect(url_for('admin.dashboard'))

    if role in ['eadmin', 'senior']:
        convener.status_text = 'rejected'
        log_access(f"{role} 拒绝了 O-Convener 的申请（ID: {id}）")

    db.session.commit()
    return redirect(url_for('admin.dashboard'))


# 退出
@adminBP.route('/logout')
def logout():
    log_access("管理员退出登录")  # ✅ 记录登出
    session.clear()
    return redirect(url_for('admin.admin_login'))

@adminBP.route('/download_proof/<filename>')
def download_proof(filename):
    upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    return send_from_directory(upload_folder, filename, as_attachment=True)

@adminBP.route('/rule/show/<filename>')
def show_rule(filename):
    upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    return send_from_directory(upload_folder, filename)

@adminBP.route('/rule/download/<filename>')
def download_rule(filename):
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

# @adminBP.route('/rule/upload', methods=['POST'])
# def upload_rule():
#     if 'admin_id' not in session or session.get('admin_role') != 'eadmin':
#         return redirect(url_for('admin.admin_login'))

#     title = request.form.get('title')
#     description = request.form.get('description', '')
#     file = request.files.get('rule_file')

#     if not file or not file.filename.endswith('.pdf'):
#         flash("请上传 PDF 文件")
#         return redirect(url_for('admin.dashboard'))

#     filename = secure_filename(file.filename)
#     filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
#     file.save(filepath)

#     new_rule = Rule(title=title, filename=filename, description=description)
#     with db.auto_commit():
#         db.session.add(new_rule)

#     flash("规则上传成功")
#     return redirect(url_for('admin.dashboard'))


# @adminBP.route('/rule/download/<filename>')
# def download_rule(filename):
#     return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename, as_attachment=True)


# @adminBP.route('/rule/delete/<int:rule_id>', methods=['POST'])
# def delete_rule(rule_id):
#     rule = Rule.query.get(rule_id)
#     if rule:
#         # 删除文件
#         filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], rule.filename)
#         if os.path.exists(filepath):
#             os.remove(filepath)
#         with db.auto_commit():
#             db.session.delete(rule)
#         flash("规则已删除")
#     return redirect(url_for('admin.dashboard'))
