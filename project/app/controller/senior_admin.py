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
        return redirect(url_for('admin.admin_login'))

    role = session.get('admin_role')

    if role == 'eadmin':
        conv_list = OConvener.query.filter_by(status_text='pending').all()
    elif role == 'senior':
        conv_list = OConvener.query.filter_by(status_text='reviewed').all()
    else:
        conv_list = []

    log_access(f"访问管理员后台（角色: {role}）")  # ✅ 记录查看后台
    return render_template('senior_admin_dashboard.html', conv_list=conv_list, role=role)


@senioradminBP.route('/approve/<int:id>', methods=['POST'])
def approve(id):
    from app import mail
    import traceback

    role = session.get('admin_role')
    if role != 'senior':
        print("[权限拒绝] 当前角色不是 senior，实际为：", role)
        return redirect(url_for('admin.admin_login'))

    convener = OConvener.query.get(id)
    if not convener:
        print(f"[数据库错误] 未找到 ID 为 {id} 的 O-Convener 用户")
        return redirect(url_for('senioradmin.dashboard'))

    convener.status_text = 'approved'
    log_access(f"✅ Senior E-Admin 审核通过注册申请（O-Convener ID: {id}）")

    try:
        subject = "E-DBA 注册审核通过通知"
        body = f"Dear {convener.org_fullname}，your O-Convener registration is approved，Welcome to E-DBA system！"
        recipient = convener.email

        print("🟡 开始准备发送邮件")
        print("➡️ 收件人:", recipient)
        print("➡️ 发件人:", current_app.config.get("MAIL_USERNAME"))
        print("➡️ 主题:", subject)
        print("➡️ 内容:", body)

        msg = Message(
            subject=subject,
            recipients=[recipient],
            body=body
        )

        with current_app.app_context():
            mail.send(msg)

        print("✅ 邮件发送成功")
        log_access(f"✅ 发送注册成功邮件至：{recipient}")

    except Exception as e:
        print("❌ 邮件发送失败：")
        traceback.print_exc()
        log_access(f"❌ 邮件发送失败至 {convener.email}：{str(e)}")

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
        log_access(f"{role} 拒绝了 O-Convener 的申请（ID: {id}）")

    db.session.commit()
    return redirect(url_for('senioradmin.dashboard'))


# 退出
@senioradminBP.route('/logout')
def logout():
    log_access("管理员退出登录")  # ✅ 记录登出
    session.clear()
    return redirect(url_for('admin.admin_login'))

@senioradminBP.route('/download_proof/<filename>')
def download_proof(filename):
    upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    return send_from_directory(upload_folder, filename, as_attachment=True)
