from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from app.models.course import Course
from app.models.student import Student
from app.models.teacher import Teacher
from app.models.base import db
from app.controller.log import log_access
from sqlalchemy import and_

courseBP = Blueprint('course', __name__, url_prefix='/course')
print("courseBP 路由已加载")

@courseBP.route('/list')
def list_courses():
    """列出课程信息，根据用户权限来决定是否可编辑"""
    user_role = session.get('user_role')
    user_id = session.get('user_id')
    user_org = session.get('user_org')
    
    if not user_role or not user_id:
        flash("请先登录")
        return redirect(url_for('user.login'))
    
    # 获取用户及其访问权限
    user = None
    if user_role == 'student':
        user = Student.query.get(user_id)
    elif user_role == 'teacher':
        user = Teacher.query.get(user_id)
    
    if not user:
        flash("用户信息异常")
        return redirect(url_for('user.login'))
    
    # 获取课程列表，默认显示自己组织的课程
    courses = Course.query.filter_by(organization=user_org).all()
    
    # 记录访问
    log_access(f"用户访问课程列表（{user_role} ID: {user_id}）")
    
    # 根据用户权限，决定是否可以编辑
    can_edit = user.access_level >= 2
    
    return render_template('course_list.html', 
                          courses=courses, 
                          user=user, 
                          can_edit=can_edit,
                          user_role=user_role)

@courseBP.route('/add', methods=['GET', 'POST'])
def add_course():
    """添加课程信息，仅access_level >= 2的用户可用"""
    user_role = session.get('user_role')
    user_id = session.get('user_id')
    user_org = session.get('user_org')
    
    if not user_role or not user_id:
        flash("请先登录")
        return redirect(url_for('user.login'))
    
    # 检查权限
    user = None
    if user_role == 'student':
        user = Student.query.get(user_id)
    elif user_role == 'teacher':
        user = Teacher.query.get(user_id)
    
    if not user or user.access_level < 2:
        flash("您没有添加课程的权限")
        return redirect(url_for('course.list_courses'))
    
    if request.method == 'GET':
        return render_template('course_form.html', course=None)
    
    # 处理POST请求
    code = request.form.get('code', '').strip()
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    credits = int(request.form.get('credits', 3))
    instructor = request.form.get('instructor', '').strip()
    
    # 验证输入
    if not code or not name:
        flash("课程代码和名称为必填项")
        return render_template('course_form.html', course=None)
    
    # 检查是否重复
    existing = Course.query.filter_by(code=code).first()
    if existing:
        flash(f"课程代码 {code} 已存在")
        return render_template('course_form.html', course=None)
    
    # 创建新课程
    new_course = Course(
        code=code,
        name=name,
        description=description,
        credits=credits,
        organization=user_org,
        instructor=instructor
    )
    
    try:
        db.session.add(new_course)
        db.session.commit()
        log_access(f"用户添加了新课程 {code}: {name}")
        flash("课程添加成功")
        return redirect(url_for('course.list_courses'))
    except Exception as e:
        db.session.rollback()
        flash(f"添加失败：{str(e)}")
        return render_template('course_form.html', course=None)

@courseBP.route('/edit/<int:course_id>', methods=['GET', 'POST'])
def edit_course(course_id):
    """编辑课程信息，仅access_level >= 2的用户可用"""
    user_role = session.get('user_role')
    user_id = session.get('user_id')
    user_org = session.get('user_org')
    
    if not user_role or not user_id:
        flash("请先登录")
        return redirect(url_for('user.login'))
    
    # 检查权限
    user = None
    if user_role == 'student':
        user = Student.query.get(user_id)
    elif user_role == 'teacher':
        user = Teacher.query.get(user_id)
    
    if not user or user.access_level < 2:
        flash("您没有编辑课程的权限")
        return redirect(url_for('course.list_courses'))
    
    # 获取课程
    course = Course.query.get_or_404(course_id)
    
    # 检查组织权限（只能编辑自己组织的课程）
    if course.organization != user_org:
        flash("您只能编辑本组织的课程")
        return redirect(url_for('course.list_courses'))
    
    if request.method == 'GET':
        return render_template('course_form.html', course=course)
    
    # 处理POST请求
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    credits = int(request.form.get('credits', 3))
    instructor = request.form.get('instructor', '').strip()
    
    # 验证输入
    if not name:
        flash("课程名称为必填项")
        return render_template('course_form.html', course=course)
    
    # 更新课程
    course.name = name
    course.description = description
    course.credits = credits
    course.instructor = instructor
    
    try:
        db.session.commit()
        log_access(f"用户编辑了课程 {course.code}: {name}")
        flash("课程更新成功")
        return redirect(url_for('course.list_courses'))
    except Exception as e:
        db.session.rollback()
        flash(f"更新失败：{str(e)}")
        return render_template('course_form.html', course=course)

@courseBP.route('/delete/<int:course_id>', methods=['POST'])
def delete_course(course_id):
    """删除课程，仅access_level >= 2的用户可用"""
    user_role = session.get('user_role')
    user_id = session.get('user_id')
    user_org = session.get('user_org')
    
    if not user_role or not user_id:
        flash("请先登录")
        return redirect(url_for('user.login'))
    
    # 检查权限
    user = None
    if user_role == 'student':
        user = Student.query.get(user_id)
    elif user_role == 'teacher':
        user = Teacher.query.get(user_id)
    
    if not user or user.access_level < 2:
        flash("您没有删除课程的权限")
        return redirect(url_for('course.list_courses'))
    
    # 获取课程
    course = Course.query.get_or_404(course_id)
    
    # 检查组织权限
    if course.organization != user_org:
        flash("您只能删除本组织的课程")
        return redirect(url_for('course.list_courses'))
    
    try:
        course_code = course.code
        course_name = course.name
        db.session.delete(course)
        db.session.commit()
        log_access(f"用户删除了课程 {course_code}: {course_name}")
        flash("课程删除成功")
    except Exception as e:
        db.session.rollback()
        flash(f"删除失败：{str(e)}")
    
    return redirect(url_for('course.list_courses'))

@courseBP.route('/view')
def view_courses():
    """只读查看课程信息，为access_level = 1的用户提供"""
    user_role = session.get('user_role')
    user_id = session.get('user_id')
    user_org = session.get('user_org')
    
    if not user_role or not user_id:
        flash("请先登录")
        return redirect(url_for('user.login'))
    
    # 获取用户信息
    user = None
    if user_role == 'student':
        user = Student.query.get(user_id)
    elif user_role == 'teacher':
        user = Teacher.query.get(user_id)
    
    if not user:
        flash("用户信息异常")
        return redirect(url_for('user.login'))
    
    # 检查权限，允许任何权限级>=1别的用户查看课程
    if user.access_level < 1:  # 只要求最低权限
        flash("您没有查看课程的权限")
        if user_role == 'student':
            return redirect(url_for('student.dashboard'))
        else:
            return redirect(url_for('teacher.dashboard'))
    
    # 获取课程列表，默认显示自己组织的课程
    courses = Course.query.filter_by(organization=user_org).all()
    
    # 记录访问
    log_access(f"用户只读查看课程列表（{user_role} ID: {user_id}）")
    
    return render_template('course_view.html', 
                          courses=courses, 
                          user=user,
                          user_role=user_role)
