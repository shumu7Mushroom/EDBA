from flask import Blueprint, render_template, request, session, redirect, url_for, flash, jsonify, current_app, send_from_directory
from app.models.rule import Rule
from app.models.base import db
from app.controller.log import log_access
from werkzeug.utils import secure_filename
from app.controller.admin_service import create_admin_account
import os

# 变量名改成 tadminBP
tadminBP = Blueprint('tadmin', __name__)

@tadminBP.route('/dashboard')
def dashboard():
    if 'admin_id' not in session or session.get('admin_role') != 'tadmin':
        return redirect(url_for('admin.admin_login'))

    rules = Rule.query.all()
    return render_template('tadmin_dashboard.html', rules=rules)

@tadminBP.route('/rule/upload', methods=['POST'])
def upload_rule():
    if 'admin_id' not in session or session.get('admin_role') != 'tadmin':
        return redirect(url_for('admin.admin_login'))

    title = request.form.get('title')
    description = request.form.get('description', '')
    file = request.files.get('rule_file')

    if not file or not file.filename.endswith('.pdf'):
        flash("Please upload a PDF file")
        return redirect(url_for('tadmin.dashboard'))

    filename = secure_filename(file.filename)
    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    new_rule = Rule(title=title, filename=filename, description=description)
    with db.auto_commit():
        db.session.add(new_rule)

    log_access(f"T-Admin uploaded rule file: {title}")
    flash("Rule uploaded successfully")
    return redirect(url_for('tadmin.dashboard'))

@tadminBP.route('/rule/download/<filename>')
def download_rule(filename):
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

@tadminBP.route('/rule/delete/<int:rule_id>', methods=['POST'])
def delete_rule(rule_id):
    if 'admin_id' not in session or session.get('admin_role') != 'tadmin':
        return redirect(url_for('admin.admin_login'))

    rule = Rule.query.get(rule_id)
    if rule:
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], rule.filename)
        if os.path.exists(filepath):
            os.remove(filepath)
        with db.auto_commit():
            db.session.delete(rule)
        log_access(f"T-Admin deleted rule file: {rule.title}")
        flash("Rule deleted")

    return redirect(url_for('tadmin.dashboard'))

@tadminBP.route('/create_admin', methods=['POST'])
def create_admin():
    data = request.form
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')
    role = data.get('role')

    if not all([name, email, password, role]):
        return jsonify({"error": "Missing required fields"}), 400

    result = create_admin_account(name, email, password, role)
    if "success" in result:
        if role == "EAdmin":
            msg = "E-Admin created successfully"
        elif role == "SeniorEAdmin":
            msg = "Senior E-Admin created successfully"
        else:
            msg = "Admin created successfully"

        return jsonify({"message": msg, "id": result['admin_id']}), 201
    else:
        return jsonify({"error": result['error']}), 400
