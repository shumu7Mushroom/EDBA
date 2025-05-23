from flask import Blueprint, render_template, request, session, flash, send_file, redirect, url_for
from app.models.student import Student
from app.models.thesis import Thesis
from app.models.base import db
from sqlalchemy import or_
import os
from flask import current_app
from app.controller.log import log_access  # ✅ 添加日志记录函数

studentBP = Blueprint('student', __name__, url_prefix='/student')

# 缓存搜索结果（如需改为 session 存储可后续改进）
thesis_results = []

@studentBP.route('', methods=['GET'])
def get_student():
    with db.auto_commit():
        student = Student('hejing', 20, 'UIC', 'hejing@mail.uic.edu.hk', '123456')
        db.session.add(student)
    log_access("插入测试学生 hejing")  # ✅ 记录行为
    return 'hello student'

@studentBP.route('/dashboard')
def dashboard():
    user_id = session.get('user_id')
    student = Student.query.get(user_id)
    log_access(f"学生访问dashboard（ID: {student.id}）")  # ✅ 记录行为
    return render_template('student_dashboard.html', student=student, theses=thesis_results)

@studentBP.route('/search', methods=['POST'])
@studentBP.route('/search', methods=['POST'])
def search_thesis():
    keywords = request.form.get('keywords', '').strip()
    user_id = session.get('user_id')
    student = Student.query.get(user_id)

    if not keywords:
        flash("Please enter keywords")
        return redirect(url_for('student.dashboard'))

    log_access(f"Students search thesis with key words: {keywords}")  # ✅ 记录行为

    # 搜索出所有匹配的论文
    all_theses = Thesis.query.filter(
        Thesis.is_check == True,
        or_(
            Thesis.title.ilike(f'%{keywords}%'),
            Thesis.abstract.ilike(f'%{keywords}%')
        )
    ).all()

    # 权限过滤
    filtered = []
    user_org = student.organization.strip()

    for thesis in all_theses:
        if thesis.access_scope == 'all':
            filtered.append(thesis.to_dict())
        elif thesis.access_scope == 'self' and thesis.organization == user_org:
            filtered.append(thesis.to_dict())
        elif thesis.access_scope == 'specific':
            specific_orgs = []
            if hasattr(thesis, 'specific_org'):
                org_raw = thesis.specific_org or ''
                # 分割逗号：英文`,`，中文`，`，空格
                org_list = [o.strip() for o in org_raw.replace('，', ',').split(',')]
                specific_orgs = [o for o in org_list if o]
            if user_org in specific_orgs:
                filtered.append(thesis.to_dict())

    global thesis_results
    thesis_results = filtered

    return render_template('student_dashboard.html', student=student, theses=thesis_results)

@studentBP.route('/purchase', methods=['POST'])
def purchase_thesis():
    title = request.form.get('title')
    user_id = session.get('user_id')

    if not user_id:
        flash("User not logged in, please login again")
        return redirect(url_for('user.login'))

    student = Student.query.get(user_id)
    if not student:
        flash("User not found, please login again")
        return redirect(url_for('user.login'))

    thesis = Thesis.query.filter_by(title=title).first()
    if not thesis:
        flash("Thesis not found")
        return redirect(url_for('student.dashboard'))

    # 限制 access_level=1 只能预览，不能下载
    if student.access_level == 1:
        flash("Your permission level only allows you to preview, not download this thesis.")
        return redirect(url_for('student.dashboard'))

    pdf_filename = thesis.pdf_path
    if not os.path.isabs(pdf_filename):
        pdf_filename = os.path.join(current_app.config['UPLOAD_FOLDER'], pdf_filename)
    pdf_filename = os.path.abspath(pdf_filename)

    if thesis.access_type != 'download':
        flash("You do not have download permission for this thesis (view only)")
        return redirect(url_for('student.dashboard'))

    if not os.path.exists(pdf_filename):
        flash("Thesis PDF file does not exist or path is incorrect")
        return redirect(url_for('student.dashboard'))

    if not thesis.is_free:
        if student.thesis_quota < thesis.price:
            flash("Insufficient quota to purchase this thesis")
            return redirect(url_for('student.dashboard'))
        else:
            student.thesis_quota -= thesis.price
            with db.auto_commit():
                db.session.add(student)
            print(f"[下载成功] {student.name} 下载了《{title}》，扣除 {thesis.price} 配额")
    else:
        print(f"[下载成功] {student.name} 下载了免费论文《{title}》")

    return send_file(pdf_filename, as_attachment=True)

@studentBP.route('/view', methods=['GET'])
def view_thesis():
    title = request.args.get('title')
    thesis = Thesis.query.filter_by(title=title).first()

    if not thesis:
        flash("Thesis does not exist")
        return redirect(url_for('student.dashboard'))

    pdf_path = thesis.pdf_path
    if not os.path.isabs(pdf_path):
        pdf_path = os.path.join(current_app.config['UPLOAD_FOLDER'], pdf_path)
    abs_path = os.path.abspath(pdf_path)

    if not os.path.exists(abs_path):
        flash("Thesis file does not exist")
        return redirect(url_for('student.dashboard'))

    # ✅ 以 inline 模式打开 PDF
    return send_file(abs_path, mimetype='application/pdf', as_attachment=False)
