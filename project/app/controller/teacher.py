from flask import Blueprint, render_template, request, session, flash, send_file, redirect, url_for, current_app
from werkzeug.utils import secure_filename
import os
from sqlalchemy import or_

from app.models.teacher import Teacher
from app.models.thesis import Thesis
from app.models.base import db
from app.controller.log import log_access  # ✅ 添加日志记录函数

teacherBP = Blueprint('teacher', __name__, url_prefix='/teacher')
ALLOWED_EXTENSIONS = {'pdf'}

# 缓存搜索结果（建议后期用 session 或数据库管理）
thesis_results = []

@teacherBP.route('', methods=['GET'])
def get_teacher():
    with db.auto_commit():
        teacher = Teacher('Nina', 18, 'CST', 'nina@uic.edu.hk', '123456')
        db.session.add(teacher)
    log_access("插入测试教师 Nina")  # ✅ 记录行为
    return 'hello teacher'

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@teacherBP.route('/dashboard', methods=['GET'])
def dashboard():
    user_id = session.get('user_id')

    db.session.expire_all()  # 清除 SQLAlchemy 缓存
    teacher = Teacher.query.filter_by(id=user_id).first()  # 避免用 .get

    if not teacher:
        flash("用户不存在，请重新登录")
        return redirect(url_for('user.login'))

    download_title = session.pop('download_title', None)
    download_path = session.pop('download_path', None)
    if download_path and os.path.exists(download_path):
        return send_file(download_path, as_attachment=True)

    return render_template(
        'teacher_dashboard.html',
        teacher=teacher,
        theses=thesis_results,
        download_title=download_title
    )


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
        Thesis.is_check == True,
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

    log_access(f"教师搜索论文关键词：{keywords}")  # ✅ 记录行为

    return render_template('teacher_dashboard.html', teacher=teacher, theses=thesis_results)


@teacherBP.route('/upload', methods=['POST'])
def upload_thesis():
    user_id = session.get('user_id')
    teacher = Teacher.query.get(user_id)

    if not teacher or teacher.access_level < 3:
        flash("您没有权限上传论文，上传功能仅限高级教师")
        return redirect(url_for('teacher.dashboard'))

    title = request.form.get('title', '').strip()
    abstract = request.form.get('abstract', '').strip()
    file = request.files.get('pdf_file')
    print("request.files keys:", list(request.files.keys()))
    print("file object:", file)
    print("filename:", file.filename if file else "No file")

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

        new_thesis = Thesis(
            title=title,
            abstract=abstract,
            pdf_path=filename,  # 相对路径，后续会拼接为绝对路径
            price=0,
            organization=teacher.organization,
            access_scope='self',
            access_type='view',
            is_free=True,
            uploader=teacher.email,  # 或者 teacher.name，根据你偏好,
            is_check=False
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

    if not user_id:
        flash("用户未登录，请重新登录")
        return redirect(url_for('user.login'))

    teacher = db.session.get(Teacher, user_id)
    if not teacher:
        flash("找不到该用户，请重新登录")
        return redirect(url_for('user.login'))

    thesis = Thesis.query.filter_by(title=title).first()
    if not thesis:
        flash("未找到该论文")
        return redirect(url_for('teacher.dashboard'))

    if thesis.access_type != 'download':
        flash("您没有该论文的下载权限（仅限查看）")
        return redirect(url_for('teacher.dashboard'))

    pdf_path = thesis.pdf_path
    if not os.path.isabs(pdf_path):
        pdf_path = os.path.join(current_app.config['UPLOAD_FOLDER'], pdf_path)
    pdf_path = os.path.abspath(pdf_path)

    if not os.path.exists(pdf_path):
        flash("论文 PDF 文件不存在或路径错误")
        return redirect(url_for('teacher.dashboard'))

    if not thesis.is_free:
        if teacher.thesis_quota < thesis.price:
            flash("下载配额不足，无法购买该论文")
            return redirect(url_for('teacher.dashboard'))
        teacher.thesis_quota -= thesis.price
        with db.auto_commit():
            db.session.add(teacher)
        log_access(f"教师 {teacher.name} 下载《{title}》，扣除 {thesis.price} 单位")
    else:
        log_access(f"教师 {teacher.name} 下载免费论文《{title}》")

    session['download_path'] = pdf_path
    session['download_title'] = title

    return redirect(url_for('teacher.dashboard'))

@teacherBP.route('/refresh', methods=['GET'])
def refresh_data():
    user_id = session.get('user_id')
    if not user_id:
        flash("请先登录")
        return redirect(url_for('user.login'))

    db.session.expire_all()
    teacher = Teacher.query.filter_by(id=user_id).first()

    if not teacher:
        flash("用户不存在")
        return redirect(url_for('user.login'))

    flash("信息已刷新")
    return redirect(url_for('teacher.dashboard'))

@teacherBP.route('/view/<filename>')
def view_pdf(filename):
    upload_folder = current_app.config['UPLOAD_FOLDER']
    file_path = os.path.join(upload_folder, filename)
    if os.path.exists(file_path):
        return send_file(file_path)
    else:
        flash("文件不存在")
        return redirect(url_for('teacher.dashboard'))
