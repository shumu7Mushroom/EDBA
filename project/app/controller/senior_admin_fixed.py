from flask import Blueprint, render_template, request, session, redirect, url_for, current_app, send_from_directory
from app.models.E_admin import EAdmin
from app.models.Senior_E_Admin import SeniorEAdmin
from app.models.o_convener import OConvener
from app.models.base import db
from app.controller.log import log_access  # ✅ 添加日志记录函数
from flask_mail import Message

senioradminBP = Blueprint('senioradmin', __name__)

# 管理后台界面
@senioradminBP.route('/dashboard')
def dashboard():
    if 'admin_id' not in session:
        return redirect(url_for('main.index'))

    role = session.get('admin_role')

    if role == 'eadmin':
        conv_list = OConvener.query.filter_by(status_text='pending').all()
    elif role == 'senior':
        conv_list = OConvener.query.filter_by(status_text='reviewed').all()
    else:
        conv_list = []

    log_access(f"Access admin dashboard (role: {role})")  # Log dashboard access
    return render_template('senior_admin_dashboard.html', conv_list=conv_list, role=role)


@senioradminBP.route('/approve/<int:id>', methods=['POST'])
def approve(id):
    from app import mail
    import traceback
    
    role = session.get('admin_role')
    if role != 'senior':
        print("[Permission Denied] Current role is not senior, actual role:", role)
        return redirect(url_for('main.index'))

    convener = OConvener.query.get(id)
    if not convener:
        print(f"[Database Error] O-Convener user with ID {id} not found")
        return redirect(url_for('senioradmin.dashboard'))

    convener.status_text = 'approved'
    log_access(f"Senior E-Admin approved registration (O-Convener ID: {id})")

    try:
        subject = "E-DBA Registration Approved Notification"
        body = f"Dear {convener.org_fullname}, your O-Convener registration is approved, Welcome to E-DBA system!"
        recipient = convener.email

        print("Start sending email")
        print("To:", recipient)
        print("From:", current_app.config.get("MAIL_USERNAME"))
        print("Subject:", subject)
        print("Body:", body)

        msg = Message(
            subject=subject,
            recipients=[recipient],
            body=body
        )

        with current_app.app_context():
            mail.send(msg)

        print("Email sent successfully")
        log_access(f"Sent registration success email to: {recipient}")

    except Exception as e:
        print("Email sending failed:")
        traceback.print_exc()
        log_access(f"Email sending failed to {convener.email}: {str(e)}")

    db.session.commit()
    return redirect(url_for('senioradmin.dashboard'))


@senioradminBP.route('/admin/reject/<int:id>', methods=['POST'])
def reject(id):
    role = session.get('admin_role')
    convener = OConvener.query.get(id)
    if not convener:
        return redirect(url_for('senioradmin.dashboard'))

    if role in ['eadmin', 'senior']:
        convener.status_text = 'rejected'
        log_access(f"{role} rejected O-Convener application (ID: {id})")

    db.session.commit()
    return redirect(url_for('senioradmin.dashboard'))


# 退出
@senioradminBP.route('/logout')
def logout():
    # Get the current role before clearing session
    role = session.get('admin_role', '')
    log_access("Admin logout")  # Log logout
    session.clear()
    # Redirect to the main index page to allow selecting any login option
    return redirect(url_for('main.index'))

@senioradminBP.route('/download_proof/<filename>')
def download_proof(filename):
    upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    return send_from_directory(upload_folder, filename, as_attachment=True)
