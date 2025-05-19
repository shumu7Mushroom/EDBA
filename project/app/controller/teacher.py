# 查询单个学生记录（GPA/成绩/身份）
from app.models.api_config import APIConfig
import pandas as pd
import requests
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
        flash("User does not exist, please login again")
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
        flash("Please enter keywords")
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

    log_access(f"Teacher search thesis with key words: {keywords}")  # ✅ 记录行为

    return render_template('teacher_dashboard.html', teacher=teacher, theses=thesis_results)


@teacherBP.route('/upload', methods=['POST'])
def upload_thesis():
    user_id = session.get('user_id')
    teacher = Teacher.query.get(user_id)

    if not teacher or teacher.access_level < 3:
        flash("You do not have permission to upload thesis, only senior teachers can upload")
        return redirect(url_for('teacher.dashboard'))

    title = request.form.get('title', '').strip()
    abstract = request.form.get('abstract', '').strip()
    file = request.files.get('pdf_file')
    print("request.files keys:", list(request.files.keys()))
    print("file object:", file)
    print("filename:", file.filename if file else "No file")

    if not title or not abstract or not file:
        flash("All fields are required")
        return redirect(url_for('teacher.dashboard'))

    if not allowed_file(file.filename):
        flash("Only PDF files are allowed")
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

        flash("Thesis uploaded successfully")
    except Exception as e:
        flash(f"Upload failed: {str(e)}")

    return redirect(url_for('teacher.dashboard'))

@teacherBP.route('/purchase', methods=['POST'])
def purchase_thesis():
    title = request.form.get('title')
    user_id = session.get('user_id')

    if not user_id:
        flash("User not logged in, please login again")
        return redirect(url_for('user.login'))

    teacher = db.session.get(Teacher, user_id)
    if not teacher:
        flash("User not found, please login again")
        return redirect(url_for('user.login'))

    thesis = Thesis.query.filter_by(title=title).first()
    if not thesis:
        flash("Thesis not found")
        return redirect(url_for('teacher.dashboard'))

    if thesis.access_type != 'download':
        flash("You do not have download permission for this thesis (view only)")
        return redirect(url_for('teacher.dashboard'))

    pdf_path = thesis.pdf_path
    if not os.path.isabs(pdf_path):
        pdf_path = os.path.join(current_app.config['UPLOAD_FOLDER'], pdf_path)
    pdf_path = os.path.abspath(pdf_path)

    if not os.path.exists(pdf_path):
        flash("Thesis PDF file does not exist or path is incorrect")
        return redirect(url_for('teacher.dashboard'))

    if not thesis.is_free:
        if teacher.thesis_quota < thesis.price:
            flash("Insufficient quota to purchase this thesis")
            return redirect(url_for('teacher.dashboard'))
        teacher.thesis_quota -= thesis.price
        with db.auto_commit():
            db.session.add(teacher)
        log_access(f"Teacher {teacher.name} download《{title}》，deduction {thesis.price} amount")
    else:
        log_access(f"Teacher {teacher.name} download free thesis《{title}》")

    session['download_path'] = pdf_path
    session['download_title'] = title

    return redirect(url_for('teacher.dashboard'))

@teacherBP.route('/refresh', methods=['GET'])
def refresh_data():
    user_id = session.get('user_id')
    if not user_id:
        flash("Please login first")
        return redirect(url_for('user.login'))

    db.session.expire_all()
    teacher = Teacher.query.filter_by(id=user_id).first()

    if not teacher:
        flash("User does not exist, please login again")
        return redirect(url_for('user.login'))

    flash("Information refreshed")
    return redirect(url_for('teacher.dashboard'))

@teacherBP.route('/view/<filename>')
def view_pdf(filename):
    upload_folder = current_app.config['UPLOAD_FOLDER']
    file_path = os.path.join(upload_folder, filename)
    if os.path.exists(file_path):
        return send_file(file_path)
    else:
        flash("File does not exist")
        return redirect(url_for('teacher.dashboard'))

# 老师查看自己上传的论文
@teacherBP.route('/mythesis')
def my_thesis():
    user_id = session.get('user_id')
    if not user_id:
        flash("请先登录")
        return redirect(url_for('user.login'))
    teacher = Teacher.query.filter_by(id=user_id).first()
    if not teacher:
        flash("User does not exist, please login again")
        return redirect(url_for('user.login'))
    # 查询自己上传的论文
    theses = Thesis.query.filter_by(uploader=teacher.email).all()
    return render_template('teacher_my_thesis.html', teacher=teacher, theses=theses)

# 论文下载接口
@teacherBP.route('/download/<filename>')
def download_pdf(filename):
    upload_folder = current_app.config['UPLOAD_FOLDER']
    file_path = os.path.join(upload_folder, filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    else:
        flash("File does not exist")
        return redirect(url_for('teacher.my_thesis'))


# 查询单个学生记录
@teacherBP.route('/query_student', methods=['GET', 'POST'])
def query_student():
    user_id = session.get('user_id')
    teacher = Teacher.query.get(user_id)
    if not teacher or teacher.access_level < 2:
        flash('No permission')
        return redirect(url_for('teacher.dashboard'))

    # 获取本组织 O-Convener 的 API 配置
    from app.models.o_convener import OConvener
    convener = OConvener.query.filter_by(org_shortname=teacher.organization).first()
    if not convener:
        flash('No O-Convener found for your organization')
        return redirect(url_for('teacher.dashboard'))
    # 只查 score 类型的 API（学生成绩/记录查询）
    configs = APIConfig.query.filter_by(institution_id=convener.id, service_type='score').all()

    name = ''
    stu_id = ''
    result = None
    api_choice = request.form.get('api_choice', 'auto') if request.method == 'POST' else 'auto'
    if request.method == 'POST':
        name = (request.form.get('name') or '').strip()
        stu_id = (request.form.get('id') or '').strip()
        if not name or not stu_id:
            flash('Name / ID cannot be empty')
        else:
            payload = {'name': name, 'id': stu_id}
            last_resp, last_cfg = None, None
            cfg_list = configs if api_choice == 'auto' else [c for c in configs if str(c.id) == str(api_choice)]
            for cfg in cfg_list:
                try:
                    url = cfg.base_url.rstrip('/') + cfg.path
                    headers = {"Content-Type": "application/json"} if '/student/record' in cfg.path else None
                    r = requests.post(url, json=payload, headers=headers, timeout=5) if headers else requests.post(url, data=payload, timeout=5)
                    if r.status_code == 200:
                        data = r.json()
                        last_resp = data
                        if data.get('status') in ('y', 'success') or 'gpa' in data:
                            result = data
                            break
                    else:
                        last_resp = {'status': 'error', 'message': f'API returned {r.status_code}'}
                except Exception as e:
                    last_resp = {'status': 'error', 'message': str(e)}
            if result is None:
                result = last_resp or {'status': 'not_found'}

    return render_template('teacher_query_student.html', name=name, stu_id=stu_id, result=result, configs=configs, api_choice=api_choice)

# 批量查询学生记录
@teacherBP.route('/query_student_batch', methods=['GET', 'POST'])
def query_student_batch():
    user_id = session.get('user_id')
    teacher = Teacher.query.get(user_id)
    if not teacher or teacher.access_level < 2:
        flash('No permission')
        return redirect(url_for('teacher.dashboard'))

    from app.models.o_convener import OConvener
    convener = OConvener.query.filter_by(org_shortname=teacher.organization).first()
    if not convener:
        flash('No O-Convener found for your organization')
        return redirect(url_for('teacher.dashboard'))
    # 只查 score 类型的 API（学生成绩/记录查询）
    configs = APIConfig.query.filter_by(institution_id=convener.id, service_type='score').all()

    results = None
    api_choice = request.form.get('api_choice', 'auto') if request.method == 'POST' else 'auto'
    if request.method == 'POST':
        file = request.files.get('file')
        if not file:
            flash('Please upload an Excel file')
        else:
            try:
                df = pd.read_excel(file)
            except Exception as e:
                flash(f'Failed to read Excel file: {str(e)}')
                return render_template('teacher_query_student_batch.html', results=None, configs=configs, api_choice=api_choice)
            results = []
            cfg_list = configs if api_choice == 'auto' else [c for c in configs if str(c.id) == str(api_choice)]
            for _, row in df.iterrows():
                name = str(row.get('name', '')).strip()
                sid = str(row.get('id', '')).strip()
                if not name or not sid:
                    results.append({**row, 'status': 'missing'})
                    continue
                payload = {'name': name, 'id': sid}
                ok = False
                last_data = None
                for cfg in cfg_list:
                    try:
                        url = cfg.base_url.rstrip('/') + cfg.path
                        headers = {"Content-Type": "application/json"} if '/student/record' in cfg.path else None
                        r = requests.post(url, json=payload, headers=headers, timeout=5) if headers else requests.post(url, data=payload, timeout=5)
                        if r.status_code == 200:
                            data = r.json()
                            last_data = data
                            if data.get('status') in ('y', 'success') or 'gpa' in data:
                                results.append({**row, **data, 'status': 'y'})
                                ok = True
                                break
                        else:
                            last_data = {'status': 'fail', 'message': f'API returned {r.status_code}'}
                    except Exception as e:
                        last_data = {'status': 'fail', 'message': str(e)}
                if not ok:
                    error_result = {**row, 'status': 'fail'}
                    if last_data and 'message' in last_data:
                        error_result['error_message'] = last_data['message']
                    results.append(error_result)

    # 保证 configs 和 api_choice 始终传递到模板
    return render_template('teacher_query_student_batch.html', results=results, configs=configs, api_choice=api_choice)