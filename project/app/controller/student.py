
from flask import Blueprint,render_template, request
from app.models.base import db
from app.models.student import Student
from flask import session, redirect, url_for
from flask import Blueprint, render_template, request, session, send_file, flash
import requests
import os
from app.models.thesis import Thesis
from app.models.base import db
from sqlalchemy import or_

studentBP = Blueprint('student',__name__)

@studentBP.route('', methods=['GET'])
def get_student():
    with db.auto_commit():
        student = Student('hejing',20,'UIC','hejing@mail.uic.edu.hk','123456')
        # 数据库的insert操作
        db.session.add(student)
    return 'hello student'

@studentBP.route('/dashboard')
def dashboard():
    return render_template('student_dashboard.html', name=session.get('user_name'))

@studentBP.route('/search', methods=['POST'])  # 同理 teacherBP 也一样
def search_thesis():
    keywords = request.form.get('keywords', '').strip()
    if not keywords:
        flash("请输入关键词")
        return redirect(url_for('student.dashboard'))  # 或 teacher.dashboard

    theses = Thesis.query.filter(
        or_(
            Thesis.title.ilike(f'%{keywords}%'),
            Thesis.abstract.ilike(f'%{keywords}%')
        )
    ).all()

    global thesis_results
    thesis_results = [t.to_dict() for t in theses]

    return render_template('student_dashboard.html', name=session.get('user_name'), theses=thesis_results)
@studentBP.route('/purchase', methods=['POST'])
def purchase_thesis():
    title = request.form.get('title')

    try:
        response = requests.get("http://172.16.160.88:8001/hw/thesis/pdf", params={"title": title})
        if response.status_code == 200:
            pdf_path = response.json()
            if isinstance(pdf_path, str) and os.path.exists(pdf_path):
                return send_file(pdf_path, as_attachment=True)
            else:
                flash('未找到该论文 PDF')
        else:
            flash('请求失败，无法下载论文')
    except Exception as e:
        flash(f'下载出错：{str(e)}')

    return render_template('student_dashboard.html', name=session.get('user_name'), theses=thesis_results)
