
from flask import Blueprint,render_template, request
from app.models.base import db
from app.models.teacher import Teacher
from flask import session
from flask import Blueprint, render_template, request, session, flash, send_file, redirect, url_for
import requests
import os
from werkzeug.utils import secure_filename
from flask import current_app
from app.models.thesis import Thesis
from app.models.base import db
from sqlalchemy import or_

teacherBP = Blueprint('teacher',__name__)
ALLOWED_EXTENSIONS = {'pdf'}

# 缓存搜索结果
thesis_results = []

@teacherBP.route('', methods=['GET'])
def get_teacher():
    with db.auto_commit():
        teacher = Teacher('Nina',18,'CST','nina@uic.edu.hk','123456')
        # 数据库的insert操作
        db.session.add(teacher)
    
    return 'hello teacher'

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@teacherBP.route('/dashboard', methods=['GET'])
def dashboard():
    return render_template('teacher_dashboard.html', name=session.get('user_name'), theses=thesis_results)

@teacherBP.route('/search', methods=['POST'])
def search_thesis():
    keywords = request.form.get('keywords', '').strip()
    if not keywords:
        flash("请输入关键词")
        return redirect(url_for('teacher.dashboard'))  # 或 teacher.dashboard

    theses = Thesis.query.filter(
        or_(
            Thesis.title.ilike(f'%{keywords}%'),
            Thesis.abstract.ilike(f'%{keywords}%')
        )
    ).all()

    global thesis_results
    thesis_results = [t.to_dict() for t in theses]

    return render_template('teacher_dashboard.html', name=session.get('user_name'), theses=thesis_results)


@teacherBP.route('/purchase', methods=['POST'])
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

    return render_template('teacher_dashboard.html', name=session.get('user_name'), theses=thesis_results)

@teacherBP.route('/upload', methods=['POST'])
def upload_thesis():
    title = request.form.get('title', '').strip()
    abstract = request.form.get('abstract', '').strip()
    file = request.files.get('pdf_file')

    if not title or not abstract or not file:
        flash("所有字段均为必填")
        return redirect(url_for('teacher.dashboard'))

    if not allowed_file(file.filename):
        flash("只允许上传 PDF 文件")
        return redirect(url_for('teacher.dashboard'))

    filename = secure_filename(file.filename)
    save_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    try:
        file.save(save_path)
        # 可以选择将 title、abstract、file path 存入数据库
        flash("论文上传成功")
    except Exception as e:
        flash(f"上传失败：{str(e)}")

    return redirect(url_for('teacher.dashboard'))