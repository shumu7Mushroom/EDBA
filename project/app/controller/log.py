from flask import Blueprint, render_template, request, session, redirect, url_for
from app.models.log import AccessLog
from app.models.base import db

logBP = Blueprint('log', __name__)
print("logBP 路由已加载")


# ————————————————————————————
# 日志查看入口
# ————————————————————————————
@logBP.route('/')
def index():
    """直接进入日志页，由 view_logs 自行判断权限"""
    return redirect(url_for('log.view_logs'))


@logBP.route('/view')
def view_logs():
    """仅限 admin 身份用户查看访问日志"""
    role = session.get('admin_role')
    if not session.get('admin_id') or role not in ['eadmin', 'senior']:
        return render_template('log_view.html', logs=[], error="权限不足，仅管理员可查看此页面。")

    logs = AccessLog.query.order_by(AccessLog.timestamp.desc()).all()
    return render_template('log_view.html', logs=logs)


# ————————————————————————————
# 通用记录函数
# ————————————————————————————
def log_access(action_desc: str):
    """通用记录访问日志"""
    user = (
        session.get('admin_name') or
        session.get('user_name') or
        '匿名'
    )
    log = AccessLog(
        user=user,
        url=request.path,
        action=action_desc,
        ip=request.remote_addr
    )
    db.session.add(log)
    db.session.commit()
