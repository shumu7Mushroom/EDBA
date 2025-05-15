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
from flask import flash
from app.controller.log import log_access  # ✅ 添加日志记录函数
import pandas as pd

oconvenerBP = Blueprint('oconvener', __name__)

@oconvenerBP.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('oconvener_register.html', title='O-Convener 注册')

    org_fullname = request.form.get('org_fullname')
    org_shortname = request.form.get('org_shortname')
    email = request.form.get('email', '').strip()
    code = request.form.get('code')
    file = request.files.get('proof')

    if not all([org_fullname, org_shortname, email, code, file]):
        return render_template('oconvener_register_fail.html', message="表单信息不完整")

    if not (email.endswith('@mail.uic.edu.cn') or email.endswith('@163.com')):
        return render_template('oconvener_register_fail.html', message="邮箱格式无效")

    if code != session.get('register_code', ''):
        return render_template('oconvener_register_fail.html', message="验证码错误")

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
    log_access(f"O-Convener 注册申请提交：{email}")  # ✅ 记录行为
    return render_template('oconvener_register_success.html', title='注册成功')


@oconvenerBP.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('oconvener_login.html', title='O-Convener 登录')

    email = request.form.get('email', '').strip()
    password = request.form.get('password', '').strip()

    convener = OConvener.query.filter_by(email=email).first()
    session['user_org'] = "o-convener"
    if not convener:
        log_access(f"O-Convener 登录失败：用户不存在（{email}）")  # ✅ 记录行为
        return render_template('oconvener_login.html', error='用户不存在')

    if convener.code != password:
        log_access(f"O-Convener 登录失败：验证码错误（{email}）")  # ✅ 记录行为
        return render_template('oconvener_login.html', error='验证码错误')

    if convener.status_text != 'approved':
        log_access(f"O-Convener 登录失败：未审核通过（{email}）")  # ✅ 记录行为
        return render_template('oconvener_login.html', error='尚未通过管理员审核，无法登录')

    # 登录成功
    session['user_id'] = convener.id
    session['user_role'] = 'convener'
    session['user_name'] = convener.org_shortname
    session['user_org'] = convener.org_fullname
    log_access(f"O-Convener 登录成功：{convener.org_shortname}（{email}）")  # ✅ 记录行为
    return redirect(url_for('oconvener.dashboard'))

@oconvenerBP.route('/send_code', methods=['POST'])
def send_code():
    from app import mail 
    email = request.form.get('email')

    allowed_domains = ['@mail.uic.edu.cn', '@163.com']
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
        print("准备发送邮件到：", email)
        print("使用发件人：", current_app.config.get("MAIL_USERNAME"))
        mail.send(msg)
        log_access(f"发送注册验证码到：{email}")  # ✅ 记录行为
        return jsonify({"status": "success", "message": "Verification code sent!"})
    except Exception as e:
        print("邮件发送失败：", type(e), e)
        return jsonify({"status": "fail", "message": "Failed to send email"}), 500

@oconvenerBP.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user_id' not in session or session.get('user_role') != 'convener':
        return redirect(url_for('oconvener.login'))

    org = session.get('user_name')  # 当前 O-Convener 的组织简称

    students = Student.query.filter_by(organization=org).all()
    teachers = Teacher.query.filter_by(organization=org).all()

    log_access(f"O-Convener 查看仪表盘：{org}")  # ✅ 记录行为
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

    db.session.commit()
    log_access(f"O-Convener 修改用户权限：{user_type} ID {user_id}")  # ✅ 记录行为
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

        log_access(f"O-Convener 上传论文：{title}")  # ✅ 记录行为
        return redirect(url_for('oconvener.list_thesis'))

    return render_template('create_thesis.html', title='上传论文')



@oconvenerBP.route('/thesis/list')
def list_thesis():
    if 'user_id' not in session or session.get('user_role') != 'convener':
        return redirect(url_for('oconvener.login'))

    convener_org = session.get('user_name')
    theses = Thesis.query.filter_by(organization=convener_org, is_check=True).all()
    log_access(f"O-Convener 查看论文列表：{convener_org}")  # ✅ 记录行为
    return render_template('list_thesis.html', title='我的论文', theses=theses)



@oconvenerBP.route('/uploads/<filename>')
def uploaded_file(filename):
    import os
    upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    print("尝试访问文件路径：", os.path.join(upload_folder, filename))  # ✅ 打印真实路径
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
    log_access(f"O-Convener 修改论文权限：{thesis.title}")  # ✅ 记录行为
    flash('论文权限已更新', 'success')
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
            flash(f"成功审核通过 {len(selected_ids)} 篇论文")
        else:
            flash("未选择任何论文")
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
                    raise ValueError("类型错误")

                with db.auto_commit():
                    pass
                flash("单个成员添加成功")
                log_access(f"O-Convener 添加成员 {email}")

            except Exception as e:
                flash(f"添加失败：{str(e)}")

            return redirect(url_for('oconvener.upload_members'))

        # === 批量 Excel 上传逻辑 ===
        file = request.files.get('excel_file')
        if not file or not file.filename.endswith('.xlsx'):
            flash("请上传有效的 Excel (.xlsx) 文件")
            return redirect(url_for('oconvener.upload_members'))

        try:
            df = pd.read_excel(file)
            required_cols = {'name', 'email', 'access_level', 'thesis_quota', 'type'}
            if not required_cols.issubset(df.columns):
                flash("Excel 表头缺少必要字段")
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
                        raise ValueError("未知类型")

                    results['success'].append(email)

                except Exception as e:
                    results['fail'].append(f"{row.get('email')} → {str(e)}")

            with db.auto_commit():
                pass

            flash(f"上传完成：成功 {len(results['success'])} 条，失败 {len(results['fail'])} 条")
            log_access(f"O-Convener 批量上传成员：成功 {len(results['success'])} 条，失败 {len(results['fail'])} 条")

        except Exception as e:
            flash(f"读取 Excel 失败：{str(e)}")

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
        flash("无效用户类型")
        return redirect(url_for('oconvener.dashboard'))

    if user:
        db.session.delete(user)
        db.session.commit()
        flash(f"成功删除 {user_type}：{user.name}")
        log_access(f"O-Convener 删除用户 {user_type}：{user.email}")
    else:
        flash("找不到该用户")

    return redirect(url_for('oconvener.dashboard'))
