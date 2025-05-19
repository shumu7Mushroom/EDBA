from flask import Blueprint, render_template, request, session, jsonify, current_app
from werkzeug.utils import secure_filename
from app.models.o_convener import OConvener
from app.models.base import db
import os
from flask_mail import Message
import random
from app.models.student import Student
from app.models.teacher import Teacher
from flask import redirect, url_for
from app.models.thesis import Thesis
from flask import send_from_directory
from flask import flash, abort,current_app
import requests
from app.controller.log import log_access  # ✅ 添加日志记录函数
import pandas as pd
from app.models.bank_config import BankConfig  # 添加这行

oconvenerBP = Blueprint('oconvener', __name__)

@oconvenerBP.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('oconvener_register.html', title='O-Convener Registration')

    org_fullname = request.form.get('org_fullname')
    org_shortname = request.form.get('org_shortname')
    email = request.form.get('email', '').strip()
    code = request.form.get('code')
    file = request.files.get('proof')

    if not all([org_fullname, org_shortname, email, code, file]):
        return render_template('oconvener_register_fail.html', message="Incomplete form information")

    if not (email.endswith('@mail.uic.edu.cn') or email.endswith('@163.com') or email.endswith('@qq.com')):
        return render_template('oconvener_register_fail.html', message="Invalid email format")

    if code != session.get('register_code', ''):
        return render_template('oconvener_register_fail.html', message="Verification code error")

    filename = secure_filename(file.filename)
    save_dir = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    os.makedirs(save_dir, exist_ok=True)
    file_path = os.path.join(save_dir, filename)
    file.save(file_path)

    new_convener = OConvener()
    new_convener.set_attrs({
        'org_fullname': org_fullname,
        'org_shortname': org_shortname,
        'email': email,
        'proof_path': file_path,
        'code': code,
        'status_text': 'pending',
        'verified': True
    })

    with db.auto_commit():
        db.session.add(new_convener)
    # session.clear()
    # session['user_role'] = "student"
    log_access(f"O-Convener registration application submitted: {email}")  # Log action
    return render_template('oconvener_register_success.html', title='Registration Successful')


@oconvenerBP.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('oconvener_login.html', title='O-Convener Login')

    email = request.form.get('email', '').strip()
    password = request.form.get('password', '').strip()

    convener = OConvener.query.filter_by(email=email).first()
    session['user_org'] = "o-convener"
    if not convener:
        log_access(f"O-Convener login failed: User does not exist ({email})")  # Log action
        return render_template('oconvener_login.html', error='User does not exist')

    if convener.code != password:
        log_access(f"O-Convener login failed: Verification code error ({email})")  # Log action
        return render_template('oconvener_login.html', error='Verification code error')

    if convener.status_text != 'approved':
        log_access(f"O-Convener login failed: Not approved ({email})")  # Log action
        return render_template('oconvener_login.html', error='Not approved by admin, unable to login')

    # 登录成功
    session['user_id'] = convener.id
    session['user_role'] = 'convener'
    session['user_name'] = convener.org_shortname
    session['user_org'] = convener.org_fullname
    log_access(f"O-Convener login successful: {convener.org_shortname} ({email})")  # Log action
    return redirect(url_for('oconvener.dashboard'))

@oconvenerBP.route('/send_code', methods=['POST'])
def send_code():
    from app import mail 
    email = request.form.get('email')

    allowed_domains = ['@mail.uic.edu.cn', '@163.com', '@qq.com']
    if not email or not any(email.endswith(domain) for domain in allowed_domains):
        return jsonify({"status": "fail", "message": "Invalid email"}), 400

    code = str(random.randint(100000, 999999))
    session['register_code'] = code

    try:
        msg = Message(
            subject="Your E-DBA Verification Code",
            recipients=[email],
            body=f"Your verification code is: {code}"
        )
        print("Preparing to send email to:", email)
        print("Using sender:", current_app.config.get("MAIL_USERNAME"))
        mail.send(msg)
        log_access(f"Sent registration verification code to: {email}")  # Log action
        return jsonify({"status": "success", "message": "Verification code sent!"})
    except Exception as e:
        print("Failed to send email:", type(e), e)
        return jsonify({"status": "fail", "message": "Failed to send email"}), 500

@oconvenerBP.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user_id' not in session or session.get('user_role') != 'convener':
        return redirect(url_for('oconvener.login'))
    convener = OConvener.query.get(session['user_id'])
    org = session.get('user_name')  # 当前 O-Convener 的组织简称
    students = Student.query.filter_by(organization=org).all()
    teachers = Teacher.query.filter_by(organization=org).all()
    log_access(f"O-Convener viewed dashboard: {org}")  # Log action
    return render_template('oconvener_dashboard.html',
                           name=org,
                           students=students,
                           teachers=teachers)


@oconvenerBP.route('/update_user/<user_type>/<int:user_id>', methods=['POST'])
def update_user(user_type, user_id):
    if user_type == 'student':
        user = Student.query.get(user_id)
    elif user_type == 'teacher':
        user = Teacher.query.get(user_id)
    else:
        return "Invalid user type", 400

    # 获取表单内容
    user.organization = request.form.get('organization')
    user.access_level = int(request.form.get('access_level', 2))
    user.thesis_quota = int(request.form.get('thesis_quota', 0))
    # 新增功能权限字段
    user.thesis_enabled = bool(request.form.get('thesis_enabled'))
    user.course_enabled = bool(request.form.get('course_enabled'))

    db.session.commit()
    log_access(f"O-Convener updated user permission: {user_type} ID {user_id}")  # Log action
    return redirect(url_for('oconvener.dashboard'))

@oconvenerBP.route('/thesis/create', methods=['GET', 'POST'])
def create_thesis():
    if 'user_id' not in session or session.get('user_role') != 'convener':
        return redirect(url_for('oconvener.login'))

    if request.method == 'POST':
        title = request.form.get('title')
        abstract = request.form.get('abstract')
        pdf_file = request.files.get('pdf_file')
        organization = session.get('user_name')  # using convener's org shortname
        access_scope = request.form.get('access_scope')  # all/specific/self
        access_type = request.form.get('access_type')    # view/download
        is_free = request.form.get('is_free') == 'true'
        price = int(request.form.get('price') or 0)
        specific_org = request.form.get('specific_org') if access_scope == 'specific' else None

        pdf_path = None
        if pdf_file and pdf_file.filename:
            filename = secure_filename(pdf_file.filename)
            upload_folder = current_app.config['UPLOAD_FOLDER']
            os.makedirs(upload_folder, exist_ok=True)
            save_path = os.path.join(upload_folder, filename)
            pdf_file.save(save_path)
            pdf_path = filename

        thesis = Thesis(
            title=title,
            abstract=abstract,
            pdf_path=pdf_path,
            organization=organization,
            access_scope=access_scope,
            access_type=access_type,
            is_free=is_free,
            price=price,
            specific_org=specific_org,
            is_check=True
        )

        with db.auto_commit():
            db.session.add(thesis)

        log_access(f"O-Convener uploaded thesis: {title}")  # Log action
        return redirect(url_for('oconvener.list_thesis'))

    return render_template('create_thesis.html', title='Upload Thesis')



@oconvenerBP.route('/thesis/list')
def list_thesis():
    if 'user_id' not in session or session.get('user_role') != 'convener':
        return redirect(url_for('oconvener.login'))

    convener_org = session.get('user_name')
    theses = Thesis.query.filter_by(organization=convener_org, is_check=True).all()
    log_access(f"O-Convener viewed thesis list: {convener_org}")  # Log action
    return render_template('list_thesis.html', title='My Theses', theses=theses)



@oconvenerBP.route('/uploads/<filename>')
def uploaded_file(filename):
    import os
    upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    print("Attempting to access file path:", os.path.join(upload_folder, filename))  # ✅ Print real path
    return send_from_directory(upload_folder, filename)

@oconvenerBP.route('/thesis/update/<int:thesis_id>', methods=['POST'])
def update_thesis(thesis_id):
    thesis = Thesis.query.get_or_404(thesis_id)

    access_scope = request.form.get('access_scope')
    access_type = request.form.get('access_type')
    is_free = request.form.get('is_free') == 'true'
    price = int(request.form.get('price', 0))

    # 自动同步逻辑
    if thesis.price == 0 and price > 0:
        is_free = False  # 如果原价为0，现在设为>0，自动取消免费
    if thesis.price > 0 and is_free:
        price = 0  # 如果原价>0，但设为免费，自动将价格设为0

    # 更新字段
    thesis.access_scope = access_scope
    thesis.access_type = access_type
    thesis.is_free = is_free
    thesis.price = price

    db.session.commit()
    log_access(f"O-Convener updated thesis permission: {thesis.title}")  # Log action
    flash('Thesis permissions updated', 'success')
    return redirect(url_for('oconvener.list_thesis'))

@oconvenerBP.route('/thesis/review', methods=['GET', 'POST'])
def review_thesis():
    if 'user_id' not in session or session.get('user_role') != 'convener':
        return redirect(url_for('oconvener.login'))

    if request.method == 'POST':
        selected_ids = request.form.getlist('thesis_id')
        if selected_ids:
            Thesis.query.filter(Thesis.id.in_(selected_ids)).update(
                {Thesis.is_check: True}, synchronize_session=False
            )
            with db.auto_commit():
                pass
            flash(f"Successfully approved {len(selected_ids)} theses")
        else:
            flash("No theses selected")
        return redirect(url_for('oconvener.review_thesis'))

    # GET：获取所有未审核论文
    theses = Thesis.query.filter_by(is_check=False).all()
    return render_template('oconvener_review_thesis.html', theses=theses)

@oconvenerBP.route('/members/upload', methods=['GET', 'POST'])
def upload_members():
    if 'user_id' not in session or session.get('user_role') != 'convener':
        return redirect(url_for('oconvener.login'))

    org = session.get('user_name')  # 当前 O-Convener 的组织名
    results = {'success': [], 'fail': []}

    if request.method == 'POST':
        # === 单个成员添加逻辑 ===

        if 'single_submit' in request.form:
            try:
                name = request.form['name'].strip()
                email = request.form['email'].strip().lower()
                access_level = int(request.form['access_level'])
                quota = int(request.form['thesis_quota'])
                user_type = request.form['type'].strip().lower()
                password = request.form.get('password', '').strip()

                if user_type == 'student':
                    user = Student.query.filter_by(email=email).first()
                    if not user:
                        # 如果填写了密码则用填写的，否则用默认123456
                        user_password = password if password else "123456"
                        user = Student(name, 0, "", email, user_password, org, access_level, quota)
                    else:
                        user.access_level = access_level
                        user.thesis_quota = quota
                        user.organization = org
                        # 如果填写了密码则更新
                        if password:
                            user.password = password
                    db.session.add(user)

                elif user_type == 'teacher':
                    user = Teacher.query.filter_by(email=email).first()
                    if not user:
                        user = Teacher(name, 0, "", email, "123456", org, access_level, quota)
                    else:
                        user.access_level = access_level
                        user.thesis_quota = quota
                        user.organization = org
                    db.session.add(user)

                else:
                    raise ValueError("Invalid type")

                with db.auto_commit():
                    pass
                flash("Single member added successfully")
                log_access(f"O-Convener added member {email}")

            except Exception as e:
                flash(f"Addition failed: {str(e)}")

            return redirect(url_for('oconvener.upload_members'))

        # === 批量 Excel 上传逻辑 ===
        file = request.files.get('excel_file')
        if not file or not file.filename.endswith('.xlsx'):
            flash("Please upload a valid Excel (.xlsx) file")
            return redirect(url_for('oconvener.upload_members'))

        try:
            df = pd.read_excel(file)
            required_cols = {'name', 'email', 'access_level', 'thesis_quota', 'type'}
            if not required_cols.issubset(df.columns):
                flash("Excel header missing required fields")
                return redirect(url_for('oconvener.upload_members'))

            for _, row in df.iterrows():
                try:
                    name = str(row['name']).strip()
                    email = str(row['email']).strip().lower()
                    access_level = int(row['access_level'])
                    quota = int(row['thesis_quota'])
                    user_type = str(row['type']).strip().lower()

                    if user_type == 'student':
                        user = Student.query.filter_by(email=email).first()
                        if not user:
                            user = Student(name, 0, "", email, "123456", org, access_level, quota)
                        else:
                            user.access_level = access_level
                            user.thesis_quota = quota
                            user.organization = org
                        db.session.add(user)

                    elif user_type == 'teacher':
                        user = Teacher.query.filter_by(email=email).first()
                        if not user:
                            user = Teacher(name, 0, "", email, "123456", org, access_level, quota)
                        else:
                            user.access_level = access_level
                            user.thesis_quota = quota
                            user.organization = org
                        db.session.add(user)

                    else:
                        raise ValueError("Unknown type")

                    results['success'].append(email)

                except Exception as e:
                    results['fail'].append(f"{row.get('email')} → {str(e)}")

            with db.auto_commit():
                pass

            flash(f"Upload complete: {len(results['success'])} successful, {len(results['fail'])} failed")
            log_access(f"O-Convener batch uploaded members: {len(results['success'])} successful, {len(results['fail'])} failed")

        except Exception as e:
            flash(f"Failed to read Excel: {str(e)}")

    return render_template("oconvener_upload_members.html", results=results)

@oconvenerBP.route('/delete_user/<user_type>/<int:user_id>', methods=['POST'])
def delete_user(user_type, user_id):
    if 'user_id' not in session or session.get('user_role') != 'convener':
        return redirect(url_for('oconvener.login'))

    if user_type == 'student':
        user = Student.query.get(user_id)
    elif user_type == 'teacher':
        user = Teacher.query.get(user_id)
    else:
        flash("Invalid user type")
        return redirect(url_for('oconvener.dashboard'))

    if user:
        db.session.delete(user)
        db.session.commit()
        flash(f"Successfully deleted {user_type}: {user.name}")
        log_access(f"O-Convener deleted user {user_type}: {user.email}")
    else:
        flash("User not found")

    return redirect(url_for('oconvener.dashboard'))

@oconvenerBP.route('/pdf/view/<filename>')
def view_pdf(filename):
    upload_folder = current_app.config['UPLOAD_FOLDER']
    file_path = os.path.join(upload_folder, filename)

    if os.path.exists(file_path):
        return send_from_directory(upload_folder, filename)
    else:
        abort(404)

@oconvenerBP.route('/pdf/download/<filename>')
def download_pdf(filename):
    upload_folder = current_app.config['UPLOAD_FOLDER']
    file_path = os.path.join(upload_folder, filename)

    if os.path.exists(file_path):
        return send_from_directory(upload_folder, filename, as_attachment=True)
    else:
        abort(404)


@oconvenerBP.route('/batch_update_students', methods=['POST'])
def batch_update_students():
    ids = request.form.get('batch_ids', '')
    action = request.form.get('batch_action', '')
    quota = request.form.get('batch_quota', '')
    org = request.form.get('batch_org', '')
    id_list = [int(i) for i in ids.split(',') if i.strip().isdigit()]
    if not id_list:
        flash("No students selected for batch operation")
        return redirect(url_for('oconvener.dashboard'))

    if action == 'update':
        thesis_enabled = request.form.get('batch_thesis_enabled')
        course_enabled = request.form.get('batch_course_enabled')
        for sid in id_list:
            student = Student.query.get(sid)
            if student:
                if quota:
                    student.thesis_quota = int(quota)
                if org:
                    student.organization = org
                # 支持批量勾选/取消勾选
                if thesis_enabled is not None:
                    student.thesis_enabled = True
                else:
                    student.thesis_enabled = False
                if course_enabled is not None:
                    student.course_enabled = True
                else:
                    student.course_enabled = False
        db.session.commit()
        flash(f"Batch update success for {len(id_list)} students")
    elif action == 'delete':
        for sid in id_list:
            student = Student.query.get(sid)
            if student:
                db.session.delete(student)
        db.session.commit()
        flash(f"Batch delete success for {len(id_list)} students")
    else:
        flash("Unknown batch action")
    return redirect(url_for('oconvener.dashboard'))

import requests
from flask import flash

@oconvenerBP.route('/pay_fee', methods=['GET', 'POST'])
def pay_fee():
    if 'user_id' not in session or session.get('user_role') != 'convener':
        return redirect(url_for('oconvener.login'))
      convener = OConvener.query.get(session['user_id'])
    
    # 获取当前用户的银行配置
    user_id = session.get('user_id')
    config = BankConfig.query.filter_by(user_id=user_id).first()
    
    # 如果没有特定用户的配置，则回退到默认配置
    if not config:
        config = BankConfig.query.first()
    
    # 更全面的配置检查
    if not config or not all([
        config.bank_name, 
        config.account_name, 
        config.bank_account, 
        config.bank_password,
        config.base_url,
        config.auth_path,
        config.transfer_path
    ]):
        flash('未配置完整的银行API信息，请先配置银行API', 'error')
        return redirect(url_for('bank_config.bank_api_config'))

    # 1. 获取该组织下未支付的学生和教师
    students = Student.query.filter_by(organization=convener.org_shortname, is_pay=0).all()
    teachers = Teacher.query.filter_by(organization=convener.org_shortname, is_pay=0).all()
    
    # 2. 准备未支付用户列表
    unpaid_users = []
    
    # 获取E-Admin设置的各级别费用
    level1_fee = config.level1_fee if config.level1_fee is not None else 20
    level2_fee = config.level2_fee if config.level2_fee is not None else 50
    level3_fee = config.level3_fee if config.level3_fee is not None else 100
    
    # 根据访问级别获取相应费用
    def get_fee_by_level(level):
        if level == 1:
            return level1_fee
        elif level == 2:
            return level2_fee
        elif level == 3:
            return level3_fee
        else:
            return level * 20  # 默认计算方式，兼容旧数据
    
    # 添加学生数据
    for student in students:
        unpaid_users.append({
            'id': f"s_{student.id}",
            'name': student.name,
            'email': student.email,
            'type': 'Student',
            'access_level': student.access_level,
            'fee': get_fee_by_level(student.access_level)
        })
    
    # 添加教师数据
    for teacher in teachers:
        unpaid_users.append({
            'id': f"t_{teacher.id}",
            'name': teacher.name,
            'email': teacher.email,
            'type': 'Teacher',
            'access_level': teacher.access_level,
            'fee': get_fee_by_level(teacher.access_level)
        })

    if request.method == 'POST':
        try:
            selected_users = request.form.getlist('selected_users')
            if not selected_users:
                flash('请选择至少一个用户进行支付', 'error')
                return render_template('pay_fee.html',
                                    config=config,
                                    organization=convener.org_shortname,
                                    unpaid_users=unpaid_users)

            # 计算选中用户的总费用
            total_fee = int(request.form.get('total_amount', 0))
            
            # 调试日志：打印配置信息
            print("Bank Config Values:")
            print(f"base_url: {config.base_url}")
            print(f"auth_path: {config.auth_path}")
            print(f"transfer_path: {config.transfer_path}")
            
            # 确保配置完整性
            if not config.base_url or not config.auth_path or not config.transfer_path:
                flash('请先完成银行API配置 (基础URL、认证路径和转账路径都是必需的)', 'error')
                return redirect(url_for('bank_config.bank_api_config'))

            # Format paths correctly
            base_url = config.base_url.rstrip('/')
            auth_path = config.auth_path.strip('/')
            transfer_path = config.transfer_path.strip('/')
            
            # 验证路径是否有效
            if not auth_path or not transfer_path:
                flash('API认证路径或转账路径格式无效', 'error')
                return redirect(url_for('bank_config.bank_api_config'))
            
            # 构建完整URL
            auth_url = f"{base_url}/{auth_path}"
            auth_data = {
                "bank": config.bank_name,
                "account_name": config.account_name,
                "account_number": config.bank_account,
                "password": config.bank_password
            }
            
            print(f"完整认证URL: {auth_url}")  # 调试日志
            print(f"认证数据: {auth_data}")  # 调试日志
            
            # 确保请求中包含requests模块
            import requests
            
            # 模拟支付开关
            mock_success = True  # 设置为True开启模拟支付，False禁用
            
            try:
                # 增加超时设置，防止长时间等待
                auth_response = requests.post(auth_url, json=auth_data, timeout=5)
                print(f"认证响应状态码: {auth_response.status_code}")  # 调试日志
                if auth_response.status_code != 200:
                    print(f"认证响应内容: {auth_response.text}")  # 调试日志，记录非200响应的内容
                    raise requests.exceptions.RequestException("认证服务返回非200状态码")
                    
                auth_result = auth_response.json()
                if auth_result['status'] != 'success':
                    flash(f'账户验证失败：{auth_result.get("reason", "未知错误")}', 'error')
                    return render_template('pay_fee.html',
                                        config=config,
                                        organization=convener.org_shortname,
                                        unpaid_users=unpaid_users)
                
                # 执行转账
                transfer_url = f"{base_url}/{transfer_path}"
                transfer_data = {
                    "from_bank": config.bank_name,
                    "from_name": config.account_name,
                    "from_account": config.bank_account,
                    "password": config.bank_password,
                    "to_bank": "E-DBA Bank",
                    "to_name": "E-DBA account",
                    "to_account": "596117071864958",  # E-admin的账号
                    "amount": total_fee
                }
                
                print(f"Transferring with URL: {transfer_url}")  # 调试日志
                print(f"Transfer data: {transfer_data}")  # 调试日志
                
                transfer_response = requests.post(transfer_url, json=transfer_data, timeout=5)
                if transfer_response.status_code != 200:
                    flash(f'转账服务暂时不可用 (HTTP {transfer_response.status_code})', 'error')
                    return render_template('pay_fee.html',
                                        config=config,
                                        organization=convener.org_shortname,
                                        unpaid_users=unpaid_users)
                
                transfer_result = transfer_response.json()
                if transfer_result['status'] != 'success':
                    flash(f'转账失败：{transfer_result.get("reason", "未知错误")}', 'error')
                    return render_template('pay_fee.html',
                                        config=config,
                                        organization=convener.org_shortname,
                                        unpaid_users=unpaid_users)
                
                # 更新选中用户的支付状态
                for user_id in selected_users:
                    type_prefix, id_num = user_id.split('_')
                    id_num = int(id_num)
                    if type_prefix == 's':
                        student = Student.query.get(id_num)
                        if student:
                            student.is_pay = 1
                    else:
                        teacher = Teacher.query.get(id_num)
                        if teacher:
                            teacher.is_pay = 1
                
                db.session.commit()
                flash('支付成功！', 'success')
                log_access(f"O-Convener {convener.org_shortname} 为 {len(selected_users)} 个用户完成支付")
                return redirect(url_for('oconvener.dashboard'))
                
            except requests.exceptions.RequestException as e:
                print(f"请求异常: {str(e)}")  # 调试日志
                flash(f'API请求失败: {str(e)}', 'error')
                
                # 如果API不可用且开启了模拟支付
                if mock_success:
                    try:
                        # 模拟成功的支付流程
                        for user_id in selected_users:
                            type_prefix, id_num = user_id.split('_')
                            id_num = int(id_num)
                            if type_prefix == 's':
                                student = Student.query.get(id_num)
                                if student:
                                    student.is_pay = 1
                            else:
                                teacher = Teacher.query.get(id_num)
                                if teacher:
                                    teacher.is_pay = 1
                        
                        db.session.commit()
                        flash('由于银行API不可用，已模拟支付成功！', 'warning')
                        log_access(f"O-Convener {convener.org_shortname} 模拟支付 {len(selected_users)} 个用户")
                        return redirect(url_for('oconvener.dashboard'))
                    except Exception as mock_error:
                        db.session.rollback()
                        flash(f'模拟支付失败: {str(mock_error)}', 'error')
                
                return render_template('pay_fee.html',
                                    config=config,
                                    organization=convener.org_shortname,
                                    unpaid_users=unpaid_users)
                
        except Exception as e:
            print("支付错误:", str(e))
            flash(f'支付过程发生错误：{str(e)}', 'error')
            db.session.rollback()
    
    return render_template('pay_fee.html',
                         config=config,
                         organization=convener.org_shortname,
                         unpaid_users=unpaid_users)

import json

@oconvenerBP.route('/save_bank_config', methods=['POST'])
def save_bank_config():
    if 'user_id' not in session or session.get('user_role') != 'convener':
        return redirect(url_for('oconvener.login'))

    # Retrieve form data
    bank_name = request.form.get('bank')
    account_name = request.form.get('account_name')
    account_number = request.form.get('account_number')
    password = request.form.get('password')
    auth_path = request.form.get('auth_path')
    transfer_path = request.form.get('transfer_path')

    # Debugging: Log retrieved form data
    print(f"Form Data - Bank: {bank_name}, Account Name: {account_name}, Account Number: {account_number}, Password: {password}, Auth Path: {auth_path}, Transfer Path: {transfer_path}")

    # Validate required fields
    if not all([bank_name, account_name, account_number, password, auth_path, transfer_path]):
        flash('请填写所有必填字段', 'error')
        return redirect(url_for('bank_config.bank_api_config'))    # Save to database
    try:
        # 获取当前用户ID
        user_id = session.get('user_id')
        
        # 按用户ID查找现有配置
        config = BankConfig.query.filter_by(user_id=user_id).first()
        # Debugging: Log initial database state
        print(f"Initial Database State: {config}")

        if not config:
            config = BankConfig(
                user_id=user_id,  # 设置关联的用户ID
                bank_name=bank_name,
                account_name=account_name,
                bank_account=account_number,
                bank_password=password,
                auth_path=auth_path,
                transfer_path=transfer_path,
                balance=0
            )
            db.session.add(config)
        else:
            config.bank_name = bank_name
            config.account_name = account_name
            config.bank_account = account_number
            config.bank_password = password
            config.auth_path = auth_path
            config.transfer_path = transfer_path

        db.session.commit()
        # Debugging: Log updated database state
        print(f"Updated Database State: {config}")
        flash('银行API配置已成功保存', 'success')
    except Exception as e:
        db.session.rollback()
        # Debugging: Log exception details
        print(f"Error while saving configuration: {str(e)}")
        flash(f'保存配置时出错: {str(e)}', 'error')

    return redirect(url_for('bank_config.bank_api_config'))