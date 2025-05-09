from flask import Blueprint, render_template, request, session, flash, send_file, redirect, url_for, current_app
from werkzeug.utils import secure_filename
import os
from sqlalchemy import or_

from app.models.teacher import Teacher
from app.models.thesis import Thesis
from app.models.base import db

teacherBP = Blueprint('teacher', __name__, url_prefix='/teacher')
ALLOWED_EXTENSIONS = {'pdf'}

# 缓存搜索结果（建议后期用 session 或数据库管理）
thesis_results = []

@teacherBP.route('', methods=['GET'])
def get_teacher():
    with db.auto_commit():
        teacher = Teacher('Nina', 18, 'CST', 'nina@uic.edu.hk', '123456')
        db.session.add(teacher)
    return 'hello teacher'

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@teacherBP.route('/dashboard', methods=['GET'])
def dashboard():
    user_id = session.get('user_id')
    teacher = Teacher.query.get(user_id)
    return render_template('teacher_dashboard.html', teacher=teacher, theses=thesis_results)

@teacherBP.route('/search', methods=['POST'])
def search_thesis():
    keywords = request.form.get('keywords', '').strip()
    user_id = session.get('user_id')
    teacher = Teacher.query.get(user_id)

    # 搜索符合关键词的论文
    theses = Thesis.query.filter(
        or_(
            Thesis.title.ilike(f'%{keywords}%'),
            Thesis.abstract.ilike(f'%{keywords}%')
        )
    ).all()

    global thesis_results
    thesis_results = [t.to_dict() for t in theses]

    return render_template('teacher_dashboard.html', teacher=teacher, theses=thesis_results)

@teacherBP.route('/purchase', methods=['POST'])
def purchase_thesis():
    title = request.form.get('title')
    user_id = session.get('user_id')
    teacher = Teacher.query.get(user_id)

    thesis = Thesis.query.filter_by(title=title).first()
    if not thesis or not thesis.pdf_path or not os.path.exists(thesis.pdf_path):
        flash("未找到论文或 PDF 文件不存在")
        return render_template('teacher_dashboard.html', teacher=teacher, theses=thesis_results)

    return send_file(thesis.pdf_path, as_attachment=True)

@teacherBP.route('/upload', methods=['POST'])
def upload_thesis():
    title = request.form.get('title', '').strip()
    abstract = request.form.get('abstract', '').strip()
    file = request.files.get('pdf_file')

    user_id = session.get('user_id')
    teacher = Teacher.query.get(user_id)

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

        # 保存论文信息到数据库
        new_thesis = Thesis(
            title=title,
            abstract=abstract,
            pdf_path=save_path,
            price=0,
            organization=teacher.organization,
            access_scope='all',
            access_type='download',
            is_free=True
        )
        with db.auto_commit():
            db.session.add(new_thesis)

        flash("论文上传成功")
    except Exception as e:
        flash(f"上传失败：{str(e)}")

    return redirect(url_for('teacher.dashboard'))
