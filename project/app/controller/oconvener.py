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
from app.controller.log import log_access  # Add log recording function
import pandas as pd
from app.models.bank_config import BankConfig  # Add this line
from app.models.E_admin import EAdmin  # Add E-Admin model

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

    # Login successful
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
        return redirect(url_for('main.index'))
    convener = OConvener.query.get(session['user_id'])
    org = session.get('user_name')  # Current O-Convener's organization abbreviation
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

    # Get form content
    user.organization = request.form.get('organization')
    user.access_level = int(request.form.get('access_level', 2))
    user.thesis_quota = int(request.form.get('thesis_quota', 0))
    # Add new feature permission fields
    user.thesis_enabled = bool(request.form.get('thesis_enabled'))
    user.course_enabled = bool(request.form.get('course_enabled'))

    db.session.commit()
    log_access(f"O-Convener updated user permission: {user_type} ID {user_id}")  # Log action
    return redirect(url_for('oconvener.dashboard'))

@oconvenerBP.route('/thesis/create', methods=['GET', 'POST'])
def create_thesis():
    if 'user_id' not in session or session.get('user_role') != 'convener':
        return redirect(url_for('main.index'))

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
        return redirect(url_for('main.index'))

    convener_org = session.get('user_name')
    theses = Thesis.query.filter_by(organization=convener_org, is_check=True).all()
    log_access(f"O-Convener viewed thesis list: {convener_org}")  # Log action
    return render_template('list_thesis.html', title='My Theses', theses=theses)



@oconvenerBP.route('/uploads/<filename>')
def uploaded_file(filename):
    import os
    upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    print("Attempting to access file path:", os.path.join(upload_folder, filename))  # Print real path
    return send_from_directory(upload_folder, filename)

@oconvenerBP.route('/thesis/update/<int:thesis_id>', methods=['POST'])
def update_thesis(thesis_id):
    thesis = Thesis.query.get_or_404(thesis_id)

    access_scope = request.form.get('access_scope')
    access_type = request.form.get('access_type')
    is_free = request.form.get('is_free') == 'true'
    price = int(request.form.get('price', 0))

    # Automatically synchronize logic
    # If the original price is 0 and now set to >0, automatically cancel free
    if thesis.price == 0 and price > 0:
        is_free = False
    # If the original price >0 but set to free, automatically set the price to 0
    if thesis.price > 0 and is_free:
        price = 0

    # Update fields
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
        return redirect(url_for('main.index'))

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

    # GET: Get all unchecked theses
    theses = Thesis.query.filter_by(is_check=False).all()
    return render_template('oconvener_review_thesis.html', theses=theses)

@oconvenerBP.route('/members/upload', methods=['GET', 'POST'])
def upload_members():
    if 'user_id' not in session or session.get('user_role') != 'convener':
        return redirect(url_for('main.index'))

    org = session.get('user_name')  # Current O-Convener's organization name
    results = {'success': [], 'fail': []}

    if request.method == 'POST':
        # === Single member addition logic ===

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
                        # If a password is provided, use it, otherwise use the default 123456
                        user_password = password if password else "123456"
                        user = Student(name, 0, "", email, user_password, org, access_level, quota)
                    else:
                        user.access_level = access_level
                        user.thesis_quota = quota
                        user.organization = org
                        # If a password is provided, update it
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

        # === Batch Excel upload logic ===
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
        return redirect(url_for('main.index'))

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
                # Support batch check/uncheck
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
        return redirect(url_for('main.index'))
    
    convener = OConvener.query.get(session['user_id'])
    
    # Common data for both GET and POST requests
    eadmin_info = {
        'bank_name': "E-DBA Bank",
        'account_name': "E-DBA account",
        'bank_account': "596117071864958"
    }
    
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
        flash('Incomplete bank API configuration, please configure the bank API first', 'error')
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
                flash('No users selected, returning to main interface', 'info')
                return redirect(url_for('oconvener.dashboard'))

            total_fee = int(request.form.get('total_amount', 0))

            # 2. Format URLs
            base_url = sender_config.base_url.rstrip('/')
            auth_url = f"{sender_config.base_url}/{sender_config.auth_path.strip('/')}"

            transfer_url = f"{base_url}/{sender_config.transfer_path.strip('/')}"

            # 3. Check receiver config
            if not receiver_config:
                flash('System has not configured E-admin receiving account information, please contact the administrator', 'error')
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

            # Debug log: Print the data passed to the external API
            print("Auth Data:", auth_data)
            # Debug log: Print the data passed to the external API (after defining transfer_data)
            

            # 5. Authenticate
            auth_response = requests.post(auth_url, json=auth_data, timeout=5)
            if auth_response.status_code != 200:
                raise requests.exceptions.RequestException("Authentication service returned non-200 status code")
            
            auth_result = auth_response.json()
            if auth_result['status'] != 'success':
                flash(f'Account verification failed: {auth_result.get("reason", "Unknown error")}', 'error')
                return render_template('pay_fee.html',
                                    config=sender_config,
                                    eadmin_info={
                                        'bank_name': receiver_config.bank_name,
                                        'account_name': receiver_config.account_name,
                                        'bank_account': receiver_config.bank_account
                                    },
                                    organization=convener.org_shortname,
                                    unpaid_users=unpaid_users)            # 6. Prepare and execute transfer
            # Use fixed E-admin account information to ensure consistency with the external API
            TO_BANK_NAME = "E-DBA Bank"
            TO_ACCOUNT_NAME = "E-DBA account"
            TO_BANK_ACCOUNT = "596117071864958"

            transfer_data = {
                "from_bank": sender_config.bank_name,
                "from_name": sender_config.account_name,
                "from_account": sender_config.bank_account,
                "account_number": sender_config.bank_account,
                "password": sender_config.bank_password,
                "to_bank": TO_BANK_NAME,                "to_name": TO_ACCOUNT_NAME,
                "to_account": TO_BANK_ACCOUNT,
                "amount": total_fee
            }
            
            print("Transfer Data:", transfer_data)
            # Debug log to verify the to_account value
            print(f"Debug: Sending to_account={transfer_data['to_account']} to external API")
            transfer_response = requests.post(transfer_url, json=transfer_data, timeout=5)
            print("📦 transfer_response.status_code =", transfer_response.status_code)
            print("📦 transfer_response.text =", transfer_response.text)
            print("🔍 Actual request transfer_url =", transfer_url)
            print("💡 Using base_url =", sender_config.base_url)
            print("💡 Request transfer path =", transfer_url)
            
            if transfer_response.status_code != 200:
                raise requests.exceptions.RequestException(f"Transfer service returned non-200 status code: {transfer_response.status_code}")
                
            transfer_result = transfer_response.json()
            if transfer_result['status'] != 'success':
                raise Exception(transfer_result.get("reason", "Transfer failed: Unknown error"))

            # Debug log to verify receiver_config values and API response
            print(f"Debug: receiver_config.bank_account={receiver_config.bank_account}")
            print(f"Debug: receiver_config.account_name={receiver_config.account_name}")
            print(f"Debug: receiver_config.bank_name={receiver_config.bank_name}")
            print(f"Debug: API Response={transfer_result}")
            
            # Update sender balance if it's returned by the API
            if 'from_balance' in transfer_result:
                sender_config.balance = transfer_result['from_balance']
                print(f"Debug: Updated sender balance from API: {sender_config.balance}")

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
                        teacher.is_pay = 1            # 8. Update balance
            # Get the balance from API response if available
            if 'from_balance' in transfer_result:
                print(f"DEBUG: API returned balance: {transfer_result['from_balance']}")
                sender_config.balance = transfer_result['from_balance']
            else:
                # Calculate locally if API doesn't return balance
                print(f"DEBUG: Calculating balance locally. Current: {sender_config.balance}, Fee: {total_fee}")
                sender_config.balance = (sender_config.balance or 0) - total_fee
                print(f"DEBUG: New calculated balance: {sender_config.balance}")

            # Update receiver's balance (E-admin)
            receiver_config.balance = (receiver_config.balance or 0) + total_fee
            db.session.commit()
              # Store payment details for display
            initial_balance = session.get('initial_balance', 0)  # Get the stored initial balance
            final_balance = sender_config.balance
            
            flash('Payment successful!', 'success')
            log_access(f"O-Convener {convener.org_shortname} completed payment for {len(selected_users)} users")
            
            # Log balance changes for debugging
            print(f"DEBUG: Initial balance: {initial_balance}, Final balance: {final_balance}, Payment amount: {total_fee}")
            
            # Render the payment page with balance information instead of redirecting
            return render_template('pay_fee.html',
                                config=sender_config,
                                eadmin_info=eadmin_info,
                                organization=convener.org_shortname,
                                unpaid_users=[],  # Empty list since users are now paid
                                payment_made=True,
                                initial_balance=initial_balance,
                                final_balance=final_balance,
                                payment_amount=total_fee)
        except requests.exceptions.RequestException as e:
            flash(f'API request failed: {str(e)}', 'error')
        except Exception as e:
            flash(f'Error occurred during payment process: {str(e)}', 'error')
            db.session.rollback()
          # Attempt to get fresh balance from API if possible
    if sender_config and sender_config.base_url and sender_config.auth_path:
        try:
            # Format auth URL
            auth_url = f"{sender_config.base_url.rstrip('/')}/{sender_config.auth_path.strip('/')}"
            
            # Auth data
            auth_data = {
                "bank": sender_config.bank_name,
                "account_name": sender_config.account_name,
                "account_number": sender_config.bank_account,
                "bank_account": sender_config.bank_account,
                "password": sender_config.bank_password
            }
            
            # Try to get current balance from API
            auth_response = requests.post(auth_url, json=auth_data, timeout=5)
            if auth_response.status_code == 200:
                auth_result = auth_response.json()
                if auth_result['status'] == 'success' and 'balance' in auth_result:
                    # Update balance from the API response
                    sender_config.balance = auth_result['balance']
                    db.session.commit()
                    print(f"DEBUG: Updated balance from API: {sender_config.balance}")
        except Exception as e:
            # If API call fails, continue with existing balance
            print(f"DEBUG: Failed to fetch balance from API: {str(e)}")
    
    # Store the current balance in session for comparison after payment
    if sender_config:
        session['initial_balance'] = sender_config.balance
    
    return render_template('pay_fee.html',
                         config=sender_config,
                         eadmin_info=eadmin_info,
                         organization=convener.org_shortname,
                         unpaid_users=unpaid_users,
                         payment_made=False)
    
@oconvenerBP.route('/save_bank_config', methods=['POST'])
def save_bank_config():
    if 'user_id' not in session or session.get('user_role') != 'convener':
        return redirect(url_for('main.index'))

    form_data = {
        'bank_name': request.form.get('bank'),
        'account_name': request.form.get('account_name'),
        'account_number': request.form.get('account_number'),
        'password': request.form.get('password'),
        'auth_path': request.form.get('auth_path'),
        'transfer_path': request.form.get('transfer_path')
    }

    if not all(form_data.values()):
        flash('Please fill in all required fields', 'error')
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
        flash('Bank API configuration has been successfully saved', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error occurred while saving configuration: {str(e)}', 'error')

    return redirect(url_for('bank_config.bank_api_config'))

@oconvenerBP.route('/set_service_fee', methods=['GET', 'POST'])
def set_service_fee():
    if 'user_id' not in session or session.get('user_role') != 'convener':
        return redirect(url_for('main.index'))
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