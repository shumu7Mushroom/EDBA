from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.models.help_request import HelpRequest
from flask_login import current_user 
from app.models.base import db
from datetime import datetime

helpBP = Blueprint('help', __name__)

@helpBP.route('/submit_help_request', methods=['GET', 'POST'])
def submit_help_request():
    if request.method == 'GET':
        # Check if user is logged in
        is_logged_in = session.get('user_id') or session.get('admin_id')
        if not is_logged_in:
            flash('Please login first.')
            return redirect(url_for('main.index'))
        
        # Use admin_role if this is an admin user, otherwise use user_role
        user_role = session.get('admin_role') or session.get('user_role')
        user_id = session.get('admin_id') or session.get('user_id')
        
        # 获取用户已有的帮助请求记录
        requests = HelpRequest.query.filter_by(
            user_type=user_role,
            user_id=user_id
        ).order_by(HelpRequest.created_at.desc()).all()
        
        return render_template('help_requests.html',
                            requests=requests,
                            is_tadmin=False,
                            user_role=user_role)

    # POST部分
    # Use admin_role if this is an admin user, otherwise use user_role
    user_type = session.get('admin_role') or session.get('user_role')
    user_id = session.get('admin_id') or session.get('user_id')
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
    # Check if user is logged in
    is_logged_in = session.get('user_id') or session.get('admin_id')
    if not is_logged_in:
        flash('Please login first.')
        return redirect(url_for('main.index'))
    
    # Use admin_role if this is an admin user, otherwise use user_role
    user_role = session.get('admin_role') or session.get('user_role')
    user_id = session.get('admin_id') or session.get('user_id')

    if user_role == 'tadmin':
        requests = HelpRequest.query.order_by(HelpRequest.created_at.desc()).all()
        is_tadmin = True
    else:
        # noraml user can only see their own requests
        requests = HelpRequest.query.filter_by(user_type=user_role, user_id=user_id) \
                    .order_by(HelpRequest.created_at.desc()).all()
        is_tadmin = False

    return render_template('help_requests.html', requests=requests, is_tadmin=is_tadmin, user_role=user_role)


@helpBP.route('/help_request/<int:id>/reply', methods=['GET', 'POST'])
def reply_help_request(id):
    # Check if user is logged in
    is_logged_in = session.get('user_id') or session.get('admin_id')
    if not is_logged_in:
        flash('Please login first.')
        return redirect(url_for('main.index'))
    
    # o convenr answer
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


@helpBP.route('/create_help_request', methods=['GET', 'POST'])
def create_help_request():
    """Universal help request function for all user types including Senior E-Admin"""
    is_logged_in = session.get('user_id') or session.get('admin_id')
    if not is_logged_in:
        flash('Please login first.')
        return redirect(url_for('main.index'))
    
    # Use admin_role if this is an admin user, otherwise use user_role
    user_role = session.get('admin_role') or session.get('user_role')
    user_id = session.get('admin_id') or session.get('user_id')
    
    if request.method == 'GET':
        # Get existing help requests for this user
        requests = HelpRequest.query.filter_by(
            user_type=user_role,
            user_id=user_id
        ).order_by(HelpRequest.created_at.desc()).all()
        
        return render_template('create_help_request.html', 
                              requests=requests,
                              user_role=user_role)
    
    # Handle POST request
    content = request.form.get('content')
    
    if not content:
        flash('Help request content cannot be empty.')
        return redirect(url_for('help.create_help_request'))
    
    new_request = HelpRequest(
        user_type=user_role,
        user_id=user_id,
        content=content,
        status='New'
    )
    
    try:
        db.session.add(new_request)
        db.session.commit()
        flash('Help request submitted successfully.')
    except Exception as e:
        db.session.rollback()
        flash(f'Error submitting help request: {str(e)}')
    
    # Redirect based on user role
    if user_role == 'senior':
        return redirect(url_for('senioradmin.dashboard'))
    elif user_role == 'eadmin':
        return redirect(url_for('admin.dashboard'))
    elif user_role == 'tadmin':
        return redirect(url_for('tadmin.dashboard'))
    elif user_role in ['student', 'teacher']:
        return redirect(url_for(f'{user_role}.dashboard'))
    elif user_role == 'convener':
        return redirect(url_for('oconvener.dashboard'))
    else:
        return redirect(url_for('help.create_help_request'))
