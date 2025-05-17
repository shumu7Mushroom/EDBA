from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.models.help_request import HelpRequest
from flask_login import current_user 
from app.models.base import db
from datetime import datetime

helpBP = Blueprint('help', __name__)

@helpBP.route('/submit_help_request', methods=['GET', 'POST'])
def submit_help_request():
    if request.method == 'GET':
        user_type = session.get('user_role')
        if user_type == 't_admin':
            # 🔁 如果是 t_admin，直接跳转到查看页面
            return redirect(url_for('help.view_help_requests'))
        
        return render_template('submit_help_request.html',
                               user_name=session.get('user_name', ''),
                               user_email=session.get('user_email', ''),
                               user_type=user_type)

    # POST部分（不改）
    user_type = session.get('user_role')
    user_id = session.get('user_id')
    content = request.form.get('content')

    if not all([user_type, user_id, content]):
        flash('Please fill in all required fields.')
        return redirect(url_for('help.submit_help_request'))

    new_request = HelpRequest(
        user_type=user_type,
        user_id=user_id,
        content=content,
        status='New'
    )
    try:
        db.session.add(new_request)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash('Database error: ' + str(e))
        return redirect(url_for('help.submit_help_request'))

    flash('Help request submitted successfully.')
    return redirect(url_for('help.submit_help_request'))

@helpBP.route('/help_requests')
def view_help_requests():
    requests = HelpRequest.query.order_by(HelpRequest.created_at.desc()).all()
    is_tadmin = session.get('user_role') == 'tadmin'  # ⬅️ 根据 session 判断角色
    return render_template('help_requests.html', requests=requests, is_tadmin=is_tadmin)


@helpBP.route('/help_request/<int:id>/reply', methods=['GET', 'POST'])
def reply_help_request(id):
    # 管理员回复问题
    question = HelpRequest.query.get_or_404(id)
    
    if request.method == 'GET':
        return render_template('reply_help_request.html', question=question)
    
    reply = request.form.get('reply')
    if not reply:
        flash('Reply content cannot be empty.')
        return redirect(url_for('help.reply_help_request', id=id))
    
    question.admin_reply = reply
    question.status = 'Resolved'
    question.replied_at = datetime.utcnow()
    db.session.commit()

    flash('Reply submitted successfully.')
    return redirect(url_for('help.view_help_requests'))
