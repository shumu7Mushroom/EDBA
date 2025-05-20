from app.models.bank_config import BankConfig
from flask import Blueprint, render_template, request, session, redirect, url_for, current_app, send_from_directory, flash
from app.models.E_admin import EAdmin
from app.models.Senior_E_Admin import SeniorEAdmin
from app.models.o_convener import OConvener
from app.models.rule import Rule
from app.models.base import db
from app.controller.log import log_access  # Add log recording function
import os
from werkzeug.utils import secure_filename
from app.models.T_admin import TAdmin

adminBP = Blueprint('admin', __name__)
print("adminBP routes loaded")


# E-Admin set bank account and membership fee
@adminBP.route('/bank_config', methods=['GET', 'POST'])
def bank_config():
    if session.get('admin_role') != 'eadmin':
        return redirect(url_for('admin.dashboard'))
    
    config = BankConfig.query.first()
    msg = None
    if request.method == 'POST':
        bank_name = request.form.get('bank_name', 'EDBA Bank')
        account_name = request.form.get('account_name', 'EDBA System')
        bank_account = request.form['bank_account']
        bank_password = request.form['bank_password']
        
        # Get fee settings for each level
        level1_fee = request.form.get('level1_fee', 20)
        level2_fee = request.form.get('level2_fee', 50)
        level3_fee = request.form.get('level3_fee', 100)
        
        if not config:
            config = BankConfig(
                bank_name=bank_name,
                account_name=account_name,
                bank_account=bank_account,
                bank_password=bank_password,
                level1_fee=level1_fee,
                level2_fee=level2_fee,
                level3_fee=level3_fee,
                balance=0
            )
            db.session.add(config)
        else:
            config.bank_name = bank_name
            config.account_name = account_name
            config.bank_account = bank_account
            config.bank_password = bank_password
            config.level1_fee = level1_fee
            config.level2_fee = level2_fee
            config.level3_fee = level3_fee
            
        db.session.commit()
        msg = "Bank account and membership fee configuration updated."
        
    return render_template('bank_config.html', config=config, msg=msg)

# Login page
@adminBP.route('/login', methods=['GET', 'POST'])
def admin_login():
    session.clear()  # Clear previous session
    if request.method == 'GET':
        return render_template('admin_login.html')
    
    email = request.form.get('email')
    password = request.form.get('password')
    role = request.form.get('role')    # Find admin based on role
    admin = None
    if role == 'eadmin':
        admin = EAdmin.query.filter_by(email=email, _password=password).first()
    elif role == 'senior':
        admin = SeniorEAdmin.query.filter_by(email=email, _password=password).first()
    elif role == 'tadmin':
        admin = TAdmin.query.filter_by(email=email, _password=password).first()

    # Verify login and set session
    if admin:
        
        session['user_id'] = admin.id
        session['user_role'] = role
        session['user_name'] = admin.name
        session['user_org'] = 'admin' 
        session['admin_id'] = admin.id
        session['admin_role'] = role
        session['admin_name'] = admin.name
        
        

        log_access(f"{role} login successful (ID: {admin.id})")

        # 👇 分开跳转
        if role == 'eadmin':
            return redirect(url_for('admin.dashboard'))
        elif role == 'senior':
            return redirect(url_for('senioradmin.dashboard'))
        elif role == 'tadmin':
            return redirect(url_for('tadmin.dashboard'))
    else:
        log_access(f"{role} login failed (email: {email})")  # Record login failure
        return render_template('admin_login.html', error='Invalid credentials')


# Admin dashboard
@adminBP.route('/dashboard')
def dashboard():
    if 'admin_id' not in session:
        return redirect(url_for('main.index'))

    role = session.get('admin_role')
    conv_list = []
    rules = []  # Prevent undefined

    if role == 'eadmin':
        conv_list = OConvener.query.filter_by(status_text='pending').all()
        rules = Rule.query.all()
    elif role == 'senior':
        conv_list = OConvener.query.filter_by(status_text='reviewed').all()

    log_access(f"Accessed admin dashboard (role: {role})")
    return render_template('admin_dashboard.html', conv_list=conv_list, role=role, rules=rules)

@adminBP.route('/approve/<int:id>', methods=['POST'])
def approve(id):
    role = session.get('admin_role')
    convener = OConvener.query.get(id)
    if not convener:
        return redirect(url_for('admin.dashboard'))

    if role == 'eadmin':
        convener.status_text = 'reviewed'
        log_access(f"E-Admin approved registration application (O-Convener ID: {id})")
    elif role == 'senior':
        convener.status_text = 'approved'
        log_access(f"Senior E-Admin approved registration application (O-Convener ID: {id})")

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
        log_access(f"{role} rejected O-Convener application (ID: {id})")

    db.session.commit()
    return redirect(url_for('admin.dashboard'))


# Logout
@adminBP.route('/logout')
def logout():
    log_access("Admin logged out")  # Record logout
    session.clear()
    return redirect(url_for('main.index'))

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
#         flash("Please upload a PDF file")
#         return redirect(url_for('admin.dashboard'))

#     filename = secure_filename(file.filename)
#     filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
#     file.save(filepath)

#     new_rule = Rule(title=title, filename=filename, description=description)
#     with db.auto_commit():
#         db.session.add(new_rule)

#     flash("Rule uploaded successfully")
#     return redirect(url_for('admin.dashboard'))


# @adminBP.route('/rule/download/<filename>')
# def download_rule(filename):
#     return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename, as_attachment=True)


# @adminBP.route('/rule/delete/<int:rule_id>', methods=['POST'])
# def delete_rule(rule_id):
#     rule = Rule.query.get(rule_id)
#     if rule:
#         # Delete file
#         filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], rule.filename)
#         if os.path.exists(filepath):
#             os.remove(filepath)
#         with db.auto_commit():
#             db.session.delete(rule)
#         flash("Rule deleted")
#     return redirect(url_for('admin.dashboard'))
