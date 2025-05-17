from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from app.models.course import Course
from app.models.student import Student
from app.models.teacher import Teacher
from app.models.base import db
from app.controller.log import log_access
from sqlalchemy import and_

courseBP = Blueprint('course', __name__, url_prefix='/course')
print("courseBP route loaded")

@courseBP.route('/list')
def list_courses():
    """List course information, determine edit permission by user access level"""
    user_role = session.get('user_role')
    user_id = session.get('user_id')
    user_org = session.get('user_org')
    
    if not user_role or not user_id:
        flash("Please login first")
        return redirect(url_for('user.login'))
    
    # Get user and access level
    user = None
    if user_role == 'student':
        user = Student.query.get(user_id)
    elif user_role == 'teacher':
        user = Teacher.query.get(user_id)
    
    if not user:
        flash("User info error")
        return redirect(url_for('user.login'))
    
    # List courses for the user's organization
    courses = Course.query.filter_by(organization=user_org).all()
    
    # Log access
    log_access(f"User accessed course list ({user_role} ID: {user_id})")
    
    can_edit = user.access_level >= 2
    
    return render_template('course_list.html', 
                          courses=courses, 
                          user=user, 
                          can_edit=can_edit,
                          user_role=user_role)

@courseBP.route('/add', methods=['GET', 'POST'])
def add_course():
    """Add course info, only for users with access_level >= 2"""
    user_role = session.get('user_role')
    user_id = session.get('user_id')
    user_org = session.get('user_org')
    
    if not user_role or not user_id:
        flash("Please login first")
        return redirect(url_for('user.login'))
    
    user = None
    if user_role == 'student':
        user = Student.query.get(user_id)
    elif user_role == 'teacher':
        user = Teacher.query.get(user_id)
    
    if not user or user.access_level < 2:
        flash("You do not have permission to add courses")
        return redirect(url_for('course.list_courses'))
    
    if request.method == 'GET':
        return render_template('course_form.html', course=None)
    
    code = request.form.get('code', '').strip()
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    credits = int(request.form.get('credits', 3))
    instructor = request.form.get('instructor', '').strip()
    
    if not code or not name:
        flash("Course code and name are required")
        return render_template('course_form.html', course=None)
    
    existing = Course.query.filter_by(code=code).first()
    if existing:
        flash(f"Course code {code} already exists")
        return render_template('course_form.html', course=None)
    
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
        log_access(f"User added new course {code}: {name}")
        flash("Course added successfully")
        return redirect(url_for('course.list_courses'))
    except Exception as e:
        db.session.rollback()
        flash(f"Add failed: {str(e)}")
        return render_template('course_form.html', course=None)

@courseBP.route('/edit/<int:course_id>', methods=['GET', 'POST'])
def edit_course(course_id):
    """Edit course info, only for users with access_level >= 2"""
    user_role = session.get('user_role')
    user_id = session.get('user_id')
    user_org = session.get('user_org')
    
    if not user_role or not user_id:
        flash("Please login first")
        return redirect(url_for('user.login'))
    
    user = None
    if user_role == 'student':
        user = Student.query.get(user_id)
    elif user_role == 'teacher':
        user = Teacher.query.get(user_id)
    
    if not user or user.access_level < 2:
        flash("You do not have permission to edit courses")
        return redirect(url_for('course.list_courses'))
    
    course = Course.query.get_or_404(course_id)
    
    if course.organization != user_org:
        flash("You can only edit courses in your organization")
        return redirect(url_for('course.list_courses'))
    
    if request.method == 'GET':
        return render_template('course_form.html', course=course)
    
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    credits = int(request.form.get('credits', 3))
    instructor = request.form.get('instructor', '').strip()
    
    if not name:
        flash("Course name is required")
        return render_template('course_form.html', course=course)
    
    course.name = name
    course.description = description
    course.credits = credits
    course.instructor = instructor
    
    try:
        db.session.commit()
        log_access(f"User edited course {course.code}: {name}")
        flash("Course updated successfully")
        return redirect(url_for('course.list_courses'))
    except Exception as e:
        db.session.rollback()
        flash(f"Update failed: {str(e)}")
        return render_template('course_form.html', course=course)

@courseBP.route('/delete/<int:course_id>', methods=['POST'])
def delete_course(course_id):
    """Delete course, only for users with access_level >= 2"""
    user_role = session.get('user_role')
    user_id = session.get('user_id')
    user_org = session.get('user_org')
    
    if not user_role or not user_id:
        flash("Please login first")
        return redirect(url_for('user.login'))
    
    user = None
    if user_role == 'student':
        user = Student.query.get(user_id)
    elif user_role == 'teacher':
        user = Teacher.query.get(user_id)
    
    if not user or user.access_level < 2:
        flash("You do not have permission to delete courses")
        return redirect(url_for('course.list_courses'))
    
    course = Course.query.get_or_404(course_id)
    
    if course.organization != user_org:
        flash("You can only delete courses in your organization")
        return redirect(url_for('course.list_courses'))
    
    try:
        course_code = course.code
        course_name = course.name
        db.session.delete(course)
        db.session.commit()
        log_access(f"User deleted course {course_code}: {course_name}")
        flash("Course deleted successfully")
    except Exception as e:
        db.session.rollback()
        flash(f"Delete failed: {str(e)}")
    
    return redirect(url_for('course.list_courses'))

@courseBP.route('/view')
def view_courses():
    """Read-only view of course info, for users with access_level >= 1"""
    user_role = session.get('user_role')
    user_id = session.get('user_id')
    user_org = session.get('user_org')
    
    if not user_role or not user_id:
        flash("Please login first")
        return redirect(url_for('user.login'))
    
    user = None
    if user_role == 'student':
        user = Student.query.get(user_id)
    elif user_role == 'teacher':
        user = Teacher.query.get(user_id)
    
    if not user:
        flash("User info error")
        return redirect(url_for('user.login'))
    
    if user.access_level < 1:
        flash("You do not have permission to view courses")
        if user_role == 'student':
            return redirect(url_for('student.dashboard'))
        else:
            return redirect(url_for('teacher.dashboard'))
    
    courses = Course.query.filter_by(organization=user_org).all()
    log_access(f"User read-only viewed course list ({user_role} ID: {user_id})")
    return render_template('course_view.html', 
                          courses=courses, 
                          user=user,
                          user_role=user_role)
