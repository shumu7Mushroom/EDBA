from flask import Blueprint, render_template, request, session, redirect, url_for, current_app, send_from_directory, flash
from app.models.E_admin import EAdmin
from app.models.Senior_E_Admin import SeniorEAdmin
from app.models.o_convener import OConvener
from app.models.rule import Rule
from app.models.base import db
from app.controller.log import log_access  # Add log record function
import os
from werkzeug.utils import secure_filename
from app.models.T_admin import TAdmin

adminBP = Blueprint('admin', __name__)
print("adminBP route loaded")

# Login page
@adminBP.route('/login', methods=['GET', 'POST'])
def admin_login():
    session.clear()  # Clear previous session
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
        log_access(f"{role} login successful (ID: {admin.id})")
        # Redirect by role
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
        log_access(f"{role} login failed (email: {email})")  # Log login failure
        return render_template('admin_login.html', error='Invalid credentials')

# Admin dashboard
@adminBP.route('/dashboard')
def dashboard():
    if 'admin_id' not in session:
        return redirect(url_for('admin.admin_login'))

    role = session.get('admin_role')
    conv_list = []
    rules = []  # Prevent undefined

    if role == 'eadmin':
        conv_list = OConvener.query.filter_by(status_text='pending').all()
        rules = Rule.query.all()
    elif role == 'senior':
        conv_list = OConvener.query.filter_by(status_text='reviewed').all()

    log_access(f"Access admin dashboard (role: {role})")
    return render_template('admin_dashboard.html', conv_list=conv_list, role=role, rules=rules)

@adminBP.route('/approve/<int:id>', methods=['POST'])
def approve(id):
    role = session.get('admin_role')
    convener = OConvener.query.get(id)
    if not convener:
        return redirect(url_for('admin.dashboard'))

    if role == 'eadmin':
        convener.status_text = 'reviewed'
        log_access(f"E-Admin approved registration (O-Convener ID: {id})")
    elif role == 'senior':
        convener.status_text = 'approved'
        log_access(f"Senior E-Admin approved registration (O-Convener ID: {id})")

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
    log_access("Admin logout")  # Log logout
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

@adminBP.route('/rule/delete/<int:rule_id>', methods=['POST'])
def delete_rule(rule_id):
    rule = Rule.query.get(rule_id)
    if rule:
        # Delete file
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], rule.filename)
        if os.path.exists(filepath):
            os.remove(filepath)
        with db.auto_commit():
            db.session.delete(rule)
        flash("Rule deleted")
    return redirect(url_for('admin.dashboard'))
