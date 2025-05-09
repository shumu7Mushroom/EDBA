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
    download_title = session.pop('download_title', None)  # ✅ 获取并移除
    return render_template('teacher_dashboard.html', teacher=teacher, theses=thesis_results, download_title=download_title)

@teacherBP.route('/search', methods=['POST'])
def search_thesis():
    keywords = request.form.get('keywords', '').strip()
    user_id = session.get('user_id')
    teacher = Teacher.query.get(user_id)

    if not keywords:
        flash("请输入关键词")
        return redirect(url_for('teacher.dashboard'))

    # 获取全部匹配论文
    all_theses = Thesis.query.filter(
        or_(
            Thesis.title.ilike(f'%{keywords}%'),
            Thesis.abstract.ilike(f'%{keywords}%')
        )
    ).all()

    # 权限过滤
    filtered = []
    user_org = teacher.organization.strip()

    for thesis in all_theses:
        if thesis.access_scope == 'all':
            filtered.append(thesis.to_dict())
        elif thesis.access_scope == 'self' and thesis.organization == user_org:
            filtered.append(thesis.to_dict())
        elif thesis.access_scope == 'specific':
            specific_orgs = []
            if hasattr(thesis, 'specific_org'):
                org_raw = thesis.specific_org or ''
                org_list = [o.strip() for o in org_raw.replace('，', ',').split(',')]
                specific_orgs = [o for o in org_list if o]
            if user_org in specific_orgs:
                filtered.append(thesis.to_dict())

    global thesis_results
    thesis_results = filtered

    return render_template('teacher_dashboard.html', teacher=teacher, theses=thesis_results)


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

@teacherBP.route('/purchase', methods=['POST'])
def purchase_thesis():
    title = request.form.get('title')
    user_id = session.get('user_id')

    # 1. 登录 & 用户检查
    if not user_id:
        flash("用户未登录，请重新登录")
        return redirect(url_for('user.login'))

    teacher = Teacher.query.get(user_id)
    if not teacher:
        flash("找不到该用户，请重新登录")
        return redirect(url_for('user.login'))

    # 2. 论文存在性检查
    thesis = Thesis.query.filter_by(title=title).first()
    if not thesis:
        flash("未找到该论文")
        return redirect(url_for('teacher.dashboard'))

    # 3. 权限检查
    if thesis.access_type != 'download':
        flash("您没有该论文的下载权限（仅限查看）")
        return redirect(url_for('teacher.dashboard'))

    # 4. 路径拼接 & 存在性检查
    pdf_path = thesis.pdf_path
    if not os.path.isabs(pdf_path):
        pdf_path = os.path.join(current_app.config['UPLOAD_FOLDER'], pdf_path)
    pdf_path = os.path.abspath(pdf_path)

    if not os.path.exists(pdf_path):
        flash("论文 PDF 文件不存在或路径错误")
        return redirect(url_for('teacher.dashboard'))

    # 5. 配额检查与扣除（非免费时）
    if not thesis.is_free:
        if teacher.thesis_quota < thesis.price:
            flash("下载配额不足，无法购买该论文")
            return redirect(url_for('teacher.dashboard'))
        # 扣配额并提交
        teacher.thesis_quota -= thesis.price
        with db.auto_commit():
            db.session.add(teacher)
        flash(f"已成功购买论文《{thesis.title}》，扣除 {thesis.price} 配额")
    else:
        flash("论文为免费，已成功下载")

    # 6. **直接返回文件流**，浏览器会弹出下载
    return send_file(pdf_path, as_attachment=True)



