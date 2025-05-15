from flask import Blueprint, render_template, request, session, redirect, url_for
from app.models.log import AccessLog
from app.models.base import db
from sqlalchemy import and_
from datetime import datetime

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
    """E-Admin / Senior 可多条件筛选，O-Convener 只能看本组织日志"""
    user_role = session.get('user_role')
    user_org = session.get('user_org')

    # 如果没有登录，或角色未知，则拒绝
    if not user_role or not user_org:
        return render_template('log_view.html', logs=[], error="未登录或身份异常，请重新登录。")

    # 获取筛选条件
    user = request.args.get('user', '').strip()
    role = request.args.get('role', '').strip()
    org = request.args.get('organization', '').strip()
    action = request.args.get('action', '').strip()
    start_time = request.args.get('start_time', '').strip()
    end_time = request.args.get('end_time', '').strip()

    # 构建基础过滤条件
    filters = []

    if user:
        filters.append(AccessLog.user.ilike(f"%{user}%"))
    if role:
        filters.append(AccessLog.role == role)
    if action:
        filters.append(AccessLog.action.ilike(f"%{action}%"))
    if start_time:
        try:
            filters.append(AccessLog.timestamp >= datetime.strptime(start_time, "%Y-%m-%d"))
        except:
            pass
    if end_time:
        try:
            filters.append(AccessLog.timestamp <= datetime.strptime(end_time, "%Y-%m-%d"))
        except:
            pass

    # 权限控制逻辑
    if user_role == 'convener':
        # 强制只能查看本组织日志，忽略用户输入的 org 参数
        filters.append(AccessLog.organization == user_org)
    else:
        # 管理员才允许按 org 过滤
        if org:
            filters.append(AccessLog.organization.ilike(f"%{org}%"))
    print("当前用户身份:", user_role, "组织:", user_org)
    print("过滤条件：", filters)

    # 执行查询
    logs = AccessLog.query.filter(and_(*filters)).order_by(AccessLog.timestamp.desc()).all()

    return render_template('log_view.html', logs=logs)




# ————————————————————————————
# 通用记录函数
# ————————————————————————————
def log_access(action_desc: str, target: str = None):
    """通用记录访问日志，可额外标记操作对象"""
    user = (
        session.get('user_name') or session.get('admin_name') or '匿名'
    )
    role =  session.get('user_role') or session.get('admin_role') or 'unknown'
    organization = session.get('user_org') or session.get('user_name') or '未知'

    log = AccessLog(
        user=user,
        role=role,
        organization=organization,
        url=request.path,
        action=action_desc,
        target=target or '',
        ip=request.remote_addr
    )
    db.session.add(log)
    db.session.commit()

