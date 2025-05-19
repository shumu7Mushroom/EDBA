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
from app.models.E_admin import EAdmin  # 添加E-Admin模型

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
    
    # Get sender's bank config (o-convener)
    user_id = session.get('user_id')
    sender_config = BankConfig.query.filter_by(user_id=user_id).first()
    
    # If no user-specific config, fallback to default
    if not sender_config:
        sender_config = BankConfig.query.filter_by(user_id=None).first()
    
    # Get receiver's bank config (E-admin, id=1)
    receiver_config = BankConfig.query.get(1)
    
    # Check both sender and receiver configs
    if not sender_config or not receiver_config or not all([
        sender_config.bank_name, 
        sender_config.account_name, 
        sender_config.bank_account, 
        sender_config.bank_password,
        sender_config.base_url,
        sender_config.auth_path,
        sender_config.transfer_path
    ]):
        flash('未配置完整的银行API信息，请先配置银行API', 'error')
        return redirect(url_for('bank_config.bank_api_config'))

    # Get unpaid students and teachers
    students = Student.query.filter_by(organization=convener.org_shortname, is_pay=0).all()
    teachers = Teacher.query.filter_by(organization=convener.org_shortname, is_pay=0).all()
    
    # Prepare unpaid users list
    unpaid_users = []
    
    # Get fee levels from the default BankConfig (id=1)
    level1_fee = receiver_config.level1_fee if receiver_config.level1_fee is not None else 2
    level2_fee = receiver_config.level2_fee if receiver_config.level2_fee is not None else 5
    level3_fee = receiver_config.level3_fee if receiver_config.level3_fee is not None else 10
    
    # Get fee by access level
    def get_fee_by_level(level):
        if level == 1:
            return level1_fee
        elif level == 2:
            return level2_fee
        elif level == 3:
            return level3_fee
        else:
            return level * 20  # Default calculation for backward compatibility
    
    # Add student data
    for student in students:
        unpaid_users.append({
            'id': f"s_{student.id}",
            'name': student.name,
            'email': student.email,
            'type': 'Student',
            'access_level': student.access_level,
            'fee': get_fee_by_level(student.access_level)
        })
    
    # Add teacher data
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
            # 1. Validate form data
            selected_users = request.form.getlist('selected_users')
            if not selected_users:
                flash('未选择任何用户，返回主界面', 'info')
                return redirect(url_for('oconvener.dashboard'))

            total_fee = int(request.form.get('total_amount', 0))

            # 2. Format URLs
            base_url = sender_config.base_url.rstrip('/')
            auth_url = f"{sender_config.base_url}/{sender_config.auth_path.strip('/')}"

            transfer_url = f"{base_url}/{sender_config.transfer_path.strip('/')}"

            # 3. Check receiver config
            if not receiver_config:
                flash('系统未配置E-admin收款账号信息，请联系管理员', 'error')
                return render_template('pay_fee.html',
                                    config=sender_config,
                                    organization=convener.org_shortname,
                                    unpaid_users=unpaid_users)

            # 4. Prepare auth data
            auth_data = {
                "bank": sender_config.bank_name,
                "account_name": sender_config.account_name,
                "account_number": sender_config.bank_account,
                "bank_account": sender_config.bank_account,
                "password": sender_config.bank_password
            }

            # 调试日志：打印传递给外部 API 的数据
            print("Auth Data:", auth_data)
            # 调试日志：打印传递给外部 API 的数据（在 transfer_data 定义后）
            

            # 5. Authenticate
            auth_response = requests.post(auth_url, json=auth_data, timeout=5)
            if auth_response.status_code != 200:
                raise requests.exceptions.RequestException("认证服务返回非200状态码")
            
            auth_result = auth_response.json()
            if auth_result['status'] != 'success':
                flash(f'账户验证失败：{auth_result.get("reason", "未知错误")}', 'error')
                return render_template('pay_fee.html',
                                    config=sender_config,
                                    eadmin_info={
                                        'bank_name': receiver_config.bank_name,
                                        'account_name': receiver_config.account_name,
                                        'bank_account': receiver_config.bank_account
                                    },
                                    organization=convener.org_shortname,
                                    unpaid_users=unpaid_users)            # 6. Prepare and execute transfer
            # 使用固定的 E-admin 账户信息，确保与外部 API 一致
            TO_BANK_NAME = "E-DBA Bank"
            TO_ACCOUNT_NAME = "E-DBA account"
            TO_BANK_ACCOUNT = "596117071864958"

            transfer_data = {
                "from_bank": sender_config.bank_name,
                "from_name": sender_config.account_name,
                "from_account": sender_config.bank_account,
                "account_number": sender_config.bank_account,
                "password": sender_config.bank_password,
                "to_bank": TO_BANK_NAME,
                "to_name": TO_ACCOUNT_NAME,
                "to_account": TO_BANK_ACCOUNT,
                "amount": total_fee
            }

            print("Transfer Data:", transfer_data)
            # Debug log to verify the to_account value
            print(f"Debug: Sending to_account={transfer_data['to_account']} to external API")
            transfer_response = requests.post(transfer_url, json=transfer_data, timeout=5)
            print("📦 transfer_response.status_code =", transfer_response.status_code)
            print("📦 transfer_response.text =", transfer_response.text)
            print("🔍 实际请求 transfer_url =", transfer_url)
            print("💡 正在使用 base_url =", sender_config.base_url)
            print("💡 请求转账路径 =", transfer_url)

            if transfer_response.status_code != 200:
                raise requests.exceptions.RequestException(f"转账服务返回非200状态码: {transfer_response.status_code}")

            transfer_result = transfer_response.json()
            if transfer_result['status'] != 'success':
                raise Exception(transfer_result.get("reason", "转账失败：未知错误"))

            # Debug log to verify receiver_config values
            print(f"Debug: receiver_config.bank_account={receiver_config.bank_account}")
            print(f"Debug: receiver_config.account_name={receiver_config.account_name}")
            print(f"Debug: receiver_config.bank_name={receiver_config.bank_name}")

            # 7. Update user payment status
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

            # 8. Update balance
            if 'from_balance' in transfer_result:
                sender_config.balance = transfer_result['from_balance']
            else:
                sender_config.balance = (sender_config.balance or 0) - total_fee

            receiver_config.balance = (receiver_config.balance or 0) + total_fee#e admin收款
            db.session.commit()
            flash('支付成功！', 'success')
            log_access(f"O-Convener {convener.org_shortname} 为 {len(selected_users)} 个用户完成支付")
            return redirect(url_for('oconvener.dashboard'))

        except requests.exceptions.RequestException as e:
            flash(f'API请求失败: {str(e)}', 'error')
        except Exception as e:
            flash(f'支付过程发生错误：{str(e)}', 'error')
            db.session.rollback()

    # GET request handling
    eadmin_info = {
        'bank_name': "E-DBA Bank",
        'account_name': "E-DBA account",
        'bank_account': "596117071864958"
    }

    return render_template('pay_fee.html',
                         config=sender_config,
                         eadmin_info=eadmin_info,
                         organization=convener.org_shortname,
                         unpaid_users=unpaid_users)
    
@oconvenerBP.route('/save_bank_config', methods=['POST'])
def save_bank_config():
    if 'user_id' not in session or session.get('user_role') != 'convener':
        return redirect(url_for('oconvener.login'))

    form_data = {
        'bank_name': request.form.get('bank'),
        'account_name': request.form.get('account_name'),
        'account_number': request.form.get('account_number'),
        'password': request.form.get('password'),
        'auth_path': request.form.get('auth_path'),
        'transfer_path': request.form.get('transfer_path')
    }

    if not all(form_data.values()):
        flash('请填写所有必填字段', 'error')
        return redirect(url_for('bank_config.bank_api_config'))

    try:
        user_id = session.get('user_id')
        config = BankConfig.query.filter_by(user_id=user_id).first()

        if not config:
            config = BankConfig(user_id=user_id, balance=0, **form_data)
            db.session.add(config)
        else:
            for key, value in form_data.items():
                setattr(config, key, value)

        db.session.commit()
        flash('银行API配置已成功保存', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'保存配置时出错: {str(e)}', 'error')

    return redirect(url_for('bank_config.bank_api_config'))

@oconvenerBP.route('/set_service_fee', methods=['GET', 'POST'])
def set_service_fee():
    if 'user_id' not in session or session.get('user_role') != 'convener':
        return redirect(url_for('oconvener.login'))
    convener = OConvener.query.get(session['user_id'])
    msg = None
    if request.method == 'POST':
        convener.identity_fee = int(request.form.get('identity_fee', 0))
        convener.score_fee = int(request.form.get('score_fee', 0))
        convener.thesis_fee = int(request.form.get('thesis_fee', 0))
        db.session.commit()
        msg = "Service fees updated successfully!"
    return render_template(
        'set_service_fee.html',
        identity_fee=convener.identity_fee or 0,
        score_fee=convener.score_fee or 0,
        thesis_fee=convener.thesis_fee or 0,
        msg=msg
    )