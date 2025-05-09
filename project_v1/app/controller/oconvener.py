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

    if not (email.endswith('@uic.edu.hk') or email.endswith('@163.com')):
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

    return render_template('oconvener_register_success.html', title='注册成功')


@oconvenerBP.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('oconvener_login.html', title='O-Convener 登录')

    email = request.form.get('email', '').strip()
    password = request.form.get('password', '').strip()

    convener = OConvener.query.filter_by(email=email).first()
    if not convener:
        return render_template('oconvener_login.html', error='用户不存在')

    if convener.code != password:
        return render_template('oconvener_login.html', error='验证码错误')

    if convener.status_text != 'approved':
        return render_template('oconvener_login.html', error='尚未通过管理员审核，无法登录')

    # 登录成功
    session['user_id'] = convener.id
    session['user_role'] = 'convener'
    session['user_name'] = convener.org_shortname
    return redirect(url_for('oconvener.dashboard'))

@oconvenerBP.route('/send_code', methods=['POST'])
def send_code():
    from app import mail 
    email = request.form.get('email')

    allowed_domains = ['@mail.uic.edu.hk', '@163.com']
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
        return jsonify({"status": "success", "message": "Verification code sent!"})
    except Exception as e:
        print("邮件发送失败：", type(e), e)
        return jsonify({"status": "fail", "message": "Failed to send email"}), 500

@oconvenerBP.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user_id' not in session or session.get('user_role') != 'convener':
        return redirect(url_for('oconvener.login'))

    students = Student.query.all()
    teachers = Teacher.query.all()
    # print(Student.query.all())
    # print(Teacher.query.all())

    return render_template('oconvener_dashboard.html',
                           name=session['user_name'],
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

        pdf_path = None
        if pdf_file and pdf_file.filename:
            filename = secure_filename(pdf_file.filename)
            upload_folder = current_app.config['UPLOAD_FOLDER']  # ✅ 用 config 中定义的绝对路径
            os.makedirs(upload_folder, exist_ok=True)
            save_path = os.path.join(upload_folder, filename)
            pdf_file.save(save_path)
            pdf_path = filename  # ✅ 仅保存文件名

        thesis = Thesis(
            title=title,
            abstract=abstract,
            pdf_path=pdf_path,
            organization=organization,
            access_scope=access_scope,
            access_type=access_type,
            is_free=is_free,
            price=price
        )

        with db.auto_commit():
            db.session.add(thesis)

        return redirect(url_for('oconvener.list_thesis'))

    return render_template('create_thesis.html', title='上传论文')


@oconvenerBP.route('/thesis/list')
def list_thesis():
    if 'user_id' not in session or session.get('user_role') != 'convener':
        return redirect(url_for('oconvener.login'))

    convener_org = session.get('user_name')
    theses = Thesis.query.filter_by(organization=convener_org).all()
    return render_template('list_thesis.html', title='我的论文', theses=theses)



@oconvenerBP.route('/uploads/<filename>')
def uploaded_file(filename):
    import os
    upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    print("尝试访问文件路径：", os.path.join(upload_folder, filename))  # ✅ 打印真实路径
    return send_from_directory(upload_folder, filename)



# @oconvenerBP.route('/api/test/students', methods=['GET'])
# def test_students():
#     from app.models.student import Student
#     students = Student.query.all()
#     return {
#         "count": len(students),
#         "students": [
#             {
#                 "id": s.id,
#                 "name": s.name,
#                 "email": s.email,
#                 "organization": getattr(s, "organization", ""),
#                 "access_level": getattr(s, "access_level", ""),
#                 "thesis_quota": getattr(s, "thesis_quota", "")
#             }
#             for s in students
#         ]
#     }
