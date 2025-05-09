from flask import Blueprint, render_template, request, session, flash, send_file, redirect, url_for
from app.models.student import Student
from app.models.thesis import Thesis
from app.models.base import db
from sqlalchemy import or_
import os

studentBP = Blueprint('student', __name__, url_prefix='/student')

# 缓存搜索结果（如需改为 session 存储可后续改进）
thesis_results = []

@studentBP.route('', methods=['GET'])
def get_student():
    with db.auto_commit():
        student = Student('hejing', 20, 'UIC', 'hejing@mail.uic.edu.hk', '123456')
        db.session.add(student)
    return 'hello student'

@studentBP.route('/dashboard')
def dashboard():
    user_id = session.get('user_id')
    student = Student.query.get(user_id)
    return render_template('student_dashboard.html', student=student, theses=thesis_results)

@studentBP.route('/search', methods=['POST'])
def search_thesis():
    keywords = request.form.get('keywords', '').strip()
    user_id = session.get('user_id')
    student = Student.query.get(user_id)

    if not keywords:
        flash("请输入关键词")
        return redirect(url_for('student.dashboard'))

    theses = Thesis.query.filter(
        or_(
            Thesis.title.ilike(f'%{keywords}%'),
            Thesis.abstract.ilike(f'%{keywords}%')
        )
    ).all()

    global thesis_results
    thesis_results = [t.to_dict() for t in theses]

    return render_template('student_dashboard.html', student=student, theses=thesis_results)

@studentBP.route('/purchase', methods=['POST'])
def purchase_thesis():
    title = request.form.get('title')
    user_id = session.get('user_id')
    student = Student.query.get(user_id)

    thesis = Thesis.query.filter_by(title=title).first()
    if not thesis or not thesis.pdf_path or not os.path.exists(thesis.pdf_path):
        flash("未找到论文或 PDF 文件不存在")
        return render_template('student_dashboard.html', student=student, theses=thesis_results)

    return send_file(thesis.pdf_path, as_attachment=True)
