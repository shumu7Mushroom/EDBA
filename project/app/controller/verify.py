# filepath: d:\GitHub\EDBA\project\app\controller\verify.py
from flask import (
    Blueprint, render_template, request, session,
    redirect, url_for, flash, send_file
)
import io, json, requests, pandas as pd
from app.models.api_config import APIConfig
from app.models.base import db
from app.controller.log import log_access

verifyBP = Blueprint('verify', __name__, url_prefix='/verify')

# ------------------------------------------------------------
# 通用工具
# ------------------------------------------------------------
def _must_convener():
    return session.get('user_role') == 'convener'

def _configs(service_type=None):
    """当前 O‑Convener 配置的接口列表"""
    q = APIConfig.query.filter_by(institution_id=session.get('user_id'))
    if service_type:
        q = q.filter_by(service_type=service_type)
    return q.all()

def _call_api(cfg, payload, files=None):
    """
    根据 cfg 调用外部接口
    - 无文件:  application/json (默认) 或 application/x-www-form-urlencoded
    - 有文件:  multipart/form-data
    """
    url = cfg.base_url.rstrip('/') + cfg.path
    try:
        # 强制thesis类型API用application/json
        is_thesis = getattr(cfg, 'service_type', None) == 'thesis'
        use_json = '/student/record' in cfg.path or is_thesis
        headers = {"Content-Type": "application/json"} if use_json else None
        
        if cfg.method.lower() == 'post':
            if files:                                   # 带照片
                r = requests.post(url, data=payload, files=files, timeout=5)
            else:
                if use_json:                            # JSON格式
                    r = requests.post(url, json=payload, headers=headers, timeout=5)
                else:                                   # 纯表单
                    r = requests.post(url, data=payload, timeout=5)
        else:                                           # GET
            r = requests.get(url, params=payload, timeout=5)

        # 检查响应状态
        if r.status_code != 200:
            # 如果不是200 OK，返回错误信息
            return {
                "status": "error",
                "message": f"API returned error: {r.status_code} {r.reason}",
                "url": url,
                "payload": payload
            }
        
        # 尝试解析返回的JSON数据
        try:
            return r.json()
        except Exception as e:
            # 如果JSON解析失败，返回错误信息
            return {
                "status": "error",
                "message": f"Failed to parse API JSON response: {str(e)}",
                "content": r.text[:200]  # 只返回前200个字符，避免过长
            }
            
    except requests.exceptions.RequestException as e:
        # 处理请求异常（连接错误、超时等）
        return {
            "status": "error",
            "message": f"Request failed: {str(e)}",
            "url": url
        }


# ------------------------------------------------------------
# 1. 接口配置  /verify/config/<service_type>
# ------------------------------------------------------------
@verifyBP.route('/config/<service_type>', methods=['GET', 'POST'])
def api_config_form(service_type):
    if not _must_convener():
        return 'Only O‑Convener can configure APIs', 403

    inst_id = session['user_id']
    configs = APIConfig.query.filter_by(institution_id=inst_id,
                                    service_type=service_type).all()
                                    
    if request.method == 'POST' and request.form.get('action') == 'add':
        base_url = request.form.get('base_url', '').strip()
        path     = request.form.get('path', '').strip()
        method   = request.form.get('method', 'POST').upper()
        input_json = request.form.get('input', '').strip()
        output_json = request.form.get('output', '').strip()
        
        # 处理 input JSON 模板
        input_data = None
        if input_json:
            try:
                input_data = json.loads(input_json)
            except json.JSONDecodeError:
                flash('Invalid input JSON format')
                return render_template('api_config_form.html',
                           configs=configs, service_type=service_type)
                
        # 处理 output JSON 模板
        output_data = None
        if output_json:
            try:
                output_data = json.loads(output_json)
            except json.JSONDecodeError:
                flash('Invalid output JSON format')
                return render_template('api_config_form.html',
                           configs=configs, service_type=service_type)
        
        # 创建新的API配置
        new_config = APIConfig(institution_id=inst_id,
                        service_type=service_type,
                        base_url=base_url, path=path, method=method,
                        input=input_data, output=output_data)
        db.session.add(new_config)
        db.session.commit()
        
        # 记录API配置添加
        log_access(f"Added new {service_type} API configuration", f"URL: {base_url}{path}")
        flash('New configuration added successfully!')
        return redirect(url_for('verify.api_config_form', service_type=service_type))

    return render_template('api_config_form.html',
                           configs=configs, service_type=service_type)

# API配置编辑
@verifyBP.route('/config/edit/<int:config_id>', methods=['GET', 'POST'])
def edit_api_config(config_id):
    if not _must_convener():
        return 'Only O‑Convener can configure APIs', 403
        
    inst_id = session['user_id']
    config = APIConfig.query.filter_by(id=config_id, institution_id=inst_id).first_or_404()
    
    if request.method == 'POST' and request.form.get('action') == 'edit':
        base_url = request.form.get('base_url', '').strip()
        path = request.form.get('path', '').strip()
        method = request.form.get('method', 'POST').upper()
        input_json = request.form.get('input', '').strip()
        output_json = request.form.get('output', '').strip()
        
        # 处理 input JSON 模板
        if input_json:
            try:
                input_data = json.loads(input_json)
                config.input = input_data
            except json.JSONDecodeError:
                flash('Invalid input JSON format')
                return render_template('edit_api_config.html', config=config)
                
        # 处理 output JSON 模板
        if output_json:
            try:
                output_data = json.loads(output_json)
                config.output = output_data
            except json.JSONDecodeError:
                flash('Invalid output JSON format')
                return render_template('edit_api_config.html', config=config)
        
        # 更新配置
        config.base_url = base_url
        config.path = path
        config.method = method
        db.session.commit()
        
        # 记录API配置更新
        log_access(f"Updated {config.service_type} API configuration", f"ID: {config_id}, URL: {base_url}{path}")
        flash('Configuration updated successfully!')
        return redirect(url_for('verify.api_config_form', service_type=config.service_type))
    
    return render_template('edit_api_config.html', config=config)

# API配置删除
@verifyBP.route('/config/delete/<int:config_id>')
def delete_api_config(config_id):
    if not _must_convener():
        return 'Only O‑Convener can configure APIs', 403
        
    inst_id = session['user_id']
    config = APIConfig.query.filter_by(id=config_id, institution_id=inst_id).first_or_404()
    service_type = config.service_type
    
    # 记录删除操作
    log_access(f"Deleted {service_type} API configuration", f"ID: {config_id}, URL: {config.base_url}{config.path}")
    
    # 删除配置
    db.session.delete(config)
    db.session.commit()
    
    flash('Configuration deleted successfully!')
    return redirect(url_for('verify.api_config_form', service_type=service_type))

# ------------------------------------------------------------
# 2. 单条学生认证 /verify/student
# ------------------------------------------------------------
@verifyBP.route('/student', methods=['GET', 'POST'])
def student_query():
    configs = _configs('identity')                      # 下拉框数据

    # ---------- 首次进入页面 ---------- #
    if request.method == 'GET':
        return render_template('verify_identity.html',
                               configs=configs,
                               api_choice='auto',
                               name='',
                               stu_id='')

    # ---------- 表单取值 ---------- #
    name = (request.form.get('name') or '').strip()
    sid  = (request.form.get('id')   or '').strip()
    api_choice = request.form.get('api_choice', 'auto')

    if not name or not sid:
        flash('Name / ID cannot be empty')
        return render_template('verify_identity.html',
                               configs=configs,
                               api_choice=api_choice,
                               name=name,
                               stu_id=sid)

    # ---------- 自动扣费逻辑 ---------- #
    user_role = session.get('user_role')
    user_id = session.get('user_id')
    user = None
    if user_role == 'teacher':
        from app.models.teacher import Teacher
        user = Teacher.query.get(user_id)
    elif user_role == 'student':
        from app.models.student import Student
        user = Student.query.get(user_id)
    organization = getattr(user, 'organization', None) if user else None
    from app.models.o_convener import OConvener
    convener = OConvener.query.filter_by(org_shortname=organization).first()
    fee = convener.identity_fee if convener else 0
    print(f"[DEBUG] [identity] user_role={user_role}, user_id={user_id}, organization={organization}, fee={fee}")
    log_access("DEBUG", f"[identity] user_role={user_role}, user_id={user_id}, organization={organization}, fee={fee}")
    if user_role in ('teacher', 'student') and fee > 0:
        print(f"[DEBUG] [identity] user object: {user}")
        log_access("DEBUG", f"[identity] user object: {user}")
        if not hasattr(user, 'thesis_quota') or user.thesis_quota is None:
            print(f"[DEBUG] [identity] user has no thesis_quota, set to 0")
            log_access("DEBUG", f"[identity] user has no thesis_quota, set to 0")
            user.thesis_quota = 0
        print(f"[DEBUG] [identity] Before deduction: user.thesis_quota={user.thesis_quota}, fee={fee}")
        log_access("DEBUG", f"[identity] Before deduction: user.thesis_quota={user.thesis_quota}, fee={fee}")
        if user.thesis_quota < fee:
            print(f"[DEBUG] [identity] Insufficient points: current={user.thesis_quota}, required={fee}")
            log_access("DEBUG", f"[identity] Insufficient points: current={user.thesis_quota}, required={fee}")
            flash(f'Insufficient points (current: {user.thesis_quota}, required: {fee}), operation denied.', 'error')
            return render_template('verify_identity.html',
                                   configs=configs,
                                   api_choice=api_choice,
                                   name=name,
                                   stu_id=sid)
        user.thesis_quota -= fee
        db.session.commit()
        print(f"[DEBUG] [identity] After deduction: user.thesis_quota={user.thesis_quota}")
        log_access("DEBUG", f"[identity] After deduction: user.thesis_quota={user.thesis_quota}")
    else:
        print(f"[DEBUG] [identity] No deduction needed for user_role={user_role}")
        log_access("DEBUG", f"[identity] No deduction needed for user_role={user_role}")

    # ---------- 处理文件 ---------- #
    photo  = request.files.get('photo')
    files  = {'photo': (photo.filename, photo.stream, photo.mimetype)
              } if photo and photo.filename else None

    payload   = {'name': name, 'id': sid}
    cfg_list  = configs if api_choice == 'auto' else \
                [APIConfig.query.get(int(api_choice))]

    last_resp, last_cfg = None, None                # 记录最后一次响应

    # ---------- 逐个接口尝试 ---------- #
    for cfg in cfg_list:
        try:
            data = _call_api(cfg, payload, files)
            last_resp, last_cfg = data, cfg
            if data.get('status') in ('y', 'success'):
                return render_template(
                    'verify_identity.html',
                    configs=configs,
                    api_choice=api_choice,
                    name=name,
                    stu_id=sid,
                    source=f'{cfg.service_type} ({cfg.method} {cfg.path})',
                    result=data
                )
        except Exception as e:
            last_resp, last_cfg = {'error': str(e)}, cfg
            continue

    # ---------- 全部接口均未命中或失败 ---------- #
    result = last_resp or {'status': 'not_found'}
    src    = f'{last_cfg.service_type} ({last_cfg.method} {last_cfg.path})' \
             if last_cfg else '—'

    return render_template('verify_identity.html',
                           configs=configs,
                           api_choice=api_choice,
                           name=name,
                           stu_id=sid,
                           source=src,
                           result=result)


# ------------------------------------------------------------
# 3. 批量认证 /verify/student/batch
# ------------------------------------------------------------
@verifyBP.route('/student/batch', methods=['POST'])
def student_batch():
    file = request.files.get('file')
    if not file:
        return 'Please upload an Excel file', 400
    df = pd.read_excel(file)

    cfgs = _configs('identity')
    if not cfgs:
        return 'No authentication interface configured', 400

    # ---------- 自动扣费逻辑 ---------- #
    user_role = session.get('user_role')
    user_id = session.get('user_id')
    user = None
    if user_role == 'teacher':
        from app.models.teacher import Teacher
        user = Teacher.query.get(user_id)
    elif user_role == 'student':
        from app.models.student import Student
        user = Student.query.get(user_id)
    organization = getattr(user, 'organization', None) if user else None
    from app.models.o_convener import OConvener
    convener = OConvener.query.filter_by(org_shortname=organization).first()
    fee = convener.identity_fee if convener else 0
    print(f"[DEBUG] [identity_batch] user_role={user_role}, user_id={user_id}, organization={organization}, fee={fee}")
    log_access("DEBUG", f"[identity_batch] user_role={user_role}, user_id={user_id}, organization={organization}, fee={fee}")
    if user_role in ('teacher', 'student') and fee > 0:
        print(f"[DEBUG] [identity_batch] user object: {user}")
        log_access("DEBUG", f"[identity_batch] user object: {user}")
        if not hasattr(user, 'thesis_quota') or user.thesis_quota is None:
            print(f"[DEBUG] [identity_batch] user has no thesis_quota, set to 0")
            log_access("DEBUG", f"[identity_batch] user has no thesis_quota, set to 0")
            user.thesis_quota = 0
        total_fee = fee * len(df)
        print(f"[DEBUG] [identity_batch] Before deduction: user.thesis_quota={user.thesis_quota}, total_fee={total_fee}")
        log_access("DEBUG", f"[identity_batch] Before deduction: user.thesis_quota={user.thesis_quota}, total_fee={total_fee}")
        if user.thesis_quota < total_fee:
            print(f"[DEBUG] [identity_batch] Insufficient points: current={user.thesis_quota}, required={total_fee}")
            log_access("DEBUG", f"[identity_batch] Insufficient points: current={user.thesis_quota}, required={total_fee}")
            flash(f'Insufficient points for batch operation (current: {user.thesis_quota}, required: {total_fee})', 'error')
            return render_template('verify_identity_batch_result.html', results=[])
        user.thesis_quota -= total_fee
        db.session.commit()
        print(f"[DEBUG] [identity_batch] After deduction: user.thesis_quota={user.thesis_quota}")
        log_access("DEBUG", f"[identity_batch] After deduction: user.thesis_quota={user.thesis_quota}")
    else:
        print(f"[DEBUG] [identity_batch] No deduction needed for user_role={user_role}")
        log_access("DEBUG", f"[identity_batch] No deduction needed for user_role={user_role}")

    results = []
    for _, row in df.iterrows():
        name = str(row.get('name', '')).strip()
        sid  = str(row.get('id',   '')).strip()
        if not name or not sid:
            results.append({**row, 'status': 'missing'})
            continue

        payload = {'name': name, 'id': sid}
        ok = False
        for cfg in cfgs:
            try:
                data = _call_api(cfg, payload)
                if data.get('status') in ('y', 'success'):
                    results.append({**row, **data, 'status': 'y'})
                    ok = True
                    break
            except Exception:
                continue
        if not ok:
            results.append({**row, 'status': 'fail'})

    session['batch_identity'] = results
    return render_template('verify_identity_batch_result.html',
                           results=results)

@verifyBP.route('/student/batch/export')
def student_batch_export():
    data = session.get('batch_identity')
    if not data:
        return 'No data to export', 400
    df = pd.DataFrame(data)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine='xlsxwriter') as w:
        df.to_excel(w, index=False, sheet_name='result')
    buf.seek(0)
    return send_file(buf, download_name='identity_batch.xlsx',
                     as_attachment=True)

# ------------------------------------------------------------
# 4. 单条学生 GPA 查询 /verify/score
# ------------------------------------------------------------
@verifyBP.route('/score', methods=['GET', 'POST'])
def score_query():
    configs = _configs('score')  # 下拉框数据

    # ---------- 首次进入页面 ---------- #
    if request.method == 'GET':
        return render_template('verify_score.html',
                               configs=configs,
                               api_choice='auto',
                               name='',
                               stu_id='')

    # ---------- 表单取值 ---------- #
    name = (request.form.get('name') or '').strip()
    sid = (request.form.get('id') or '').strip()
    api_choice = request.form.get('api_choice', 'auto')

    if not name or not sid:
        flash('Name / ID cannot be empty')
        # 直接回渲染页面而非 redirect，避免丢失输入
        return render_template('verify_score.html',
                               configs=configs,
                               api_choice=api_choice,
                               name=name,
                               stu_id=sid)

    # ---------- 自动扣费逻辑 ---------- #
    user_role = session.get('user_role')
    user_id = session.get('user_id')
    user = None
    if user_role == 'teacher':
        from app.models.teacher import Teacher
        user = Teacher.query.get(user_id)
    elif user_role == 'student':
        from app.models.student import Student
        user = Student.query.get(user_id)
    organization = getattr(user, 'organization', None) if user else None
    from app.models.o_convener import OConvener
    convener = OConvener.query.filter_by(org_shortname=organization).first()
    fee = convener.score_fee if convener else 0
    print(f"[DEBUG] [score] user_role={user_role}, user_id={user_id}, organization={organization}, fee={fee}")
    log_access("DEBUG", f"[score] user_role={user_role}, user_id={user_id}, organization={organization}, fee={fee}")
    if user_role in ('teacher', 'student') and fee > 0:
        print(f"[DEBUG] [score] user object: {user}")
        log_access("DEBUG", f"[score] user object: {user}")
        if not hasattr(user, 'thesis_quota') or user.thesis_quota is None:
            print(f"[DEBUG] [score] user has no thesis_quota, set to 0")
            log_access("DEBUG", f"[score] user has no thesis_quota, set to 0")
            user.thesis_quota = 0
        print(f"[DEBUG] [score] Before deduction: user.thesis_quota={user.thesis_quota}, fee={fee}")
        log_access("DEBUG", f"[score] Before deduction: user.thesis_quota={user.thesis_quota}, fee={fee}")
        if user.thesis_quota < fee:
            print(f"[DEBUG] [score] Insufficient points: current={user.thesis_quota}, required={fee}")
            log_access("DEBUG", f"[score] Insufficient points: current={user.thesis_quota}, required={fee}")
            flash(f'Insufficient points (current: {user.thesis_quota}, required: {fee}), operation denied.', 'error')
            return render_template('verify_score.html',
                                   configs=configs,
                                   api_choice=api_choice,
                                   name=name,
                                   stu_id=sid)
        user.thesis_quota -= fee
        db.session.commit()
        print(f"[DEBUG] [score] After deduction: user.thesis_quota={user.thesis_quota}")
        log_access("DEBUG", f"[score] After deduction: user.thesis_quota={user.thesis_quota}")
    else:
        print(f"[DEBUG] [score] No deduction needed for user_role={user_role}")
        log_access("DEBUG", f"[score] No deduction needed for user_role={user_role}")

    payload = {'name': name, 'id': sid}
    cfg_list = configs if api_choice == 'auto' else \
        [APIConfig.query.get(int(api_choice))]

    last_resp, last_cfg = None, None  # 记录最后一次响应    # ---------- 逐个接口尝试 ---------- #
    for cfg in cfg_list:
        try:
            data = _call_api(cfg, payload)
            last_resp, last_cfg = data, cfg
            
            # 检查是否为有效响应
            if data.get('status') in ('y', 'success') or 'gpa' in data:
                # 如果返回了GPA数据但没有status字段，添加成功标志
                if 'gpa' in data and 'status' not in data:
                    data['status'] = 'success'
                    # 确保必要的字段存在
                    if 'id' not in data:
                        data['id'] = sid
                    if 'name' not in data:
                        data['name'] = name
                    if 'major' not in data and 'enroll_year' in data:
                        data['major'] = f"{data.get('enroll_year', '')}-{data.get('graduation_year', '')} student"
                
                # 记录成功查询的日志
                log_access(f"Query student GPA", f"Student: {name}({sid})")
                return render_template(
                    'verify_score.html',
                    configs=configs,
                    api_choice=api_choice,
                    name=name,
                    stu_id=sid,
                    source=f'{cfg.service_type} ({cfg.method} {cfg.path})',
                    result=data
                )
        except Exception as e:
            last_resp, last_cfg = {'error': str(e)}, cfg
            continue

    # ---------- 全部接口均未命中或失败 ---------- #
    result = last_resp or {'status': 'not_found'}
    src = f'{last_cfg.service_type} ({last_cfg.method} {last_cfg.path})' \
        if last_cfg else '—'

    return render_template('verify_score.html',
                          configs=configs,
                          api_choice=api_choice,
                          name=name,
                          stu_id=sid,
                          source=src,
                          result=result)


# ------------------------------------------------------------
# 5. 批量 GPA 查询 /verify/score/batch
# ------------------------------------------------------------
@verifyBP.route('/score/batch', methods=['POST'])
def score_batch():
    file = request.files.get('file')
    if not file:
        flash('Please upload an Excel file')
        return redirect(url_for('verify.score_query'))
        
    try:
        df = pd.read_excel(file)
    except Exception as e:
        flash(f'Failed to read Excel file: {str(e)}')
        return redirect(url_for('verify.score_query'))

    cfgs = _configs('score')
    if not cfgs:
        flash('No GPA query API configured, please configure first')
        return redirect(url_for('verify.score_query'))

    # 记录批量查询日志
    log_access(f"Batch query student GPA", f"Total {len(df)} records")

    # ---------- 自动扣费逻辑 ---------- #
    user_role = session.get('user_role')
    user_id = session.get('user_id')
    user = None
    if user_role == 'teacher':
        from app.models.teacher import Teacher
        user = Teacher.query.get(user_id)
    elif user_role == 'student':
        from app.models.student import Student
        user = Student.query.get(user_id)
    organization = getattr(user, 'organization', None) if user else None
    from app.models.o_convener import OConvener
    convener = OConvener.query.filter_by(org_shortname=organization).first()
    fee = convener.score_fee if convener else 0
    print(f"[DEBUG] [score_batch] user_role={user_role}, user_id={user_id}, organization={organization}, fee={fee}")
    log_access("DEBUG", f"[score_batch] user_role={user_role}, user_id={user_id}, organization={organization}, fee={fee}")
    if user_role in ('teacher', 'student') and fee > 0:
        print(f"[DEBUG] [score_batch] user object: {user}")
        log_access("DEBUG", f"[score_batch] user object: {user}")
        if not hasattr(user, 'thesis_quota') or user.thesis_quota is None:
            print(f"[DEBUG] [score_batch] user has no thesis_quota, set to 0")
            log_access("DEBUG", f"[score_batch] user has no thesis_quota, set to 0")
            user.thesis_quota = 0
        total_fee = fee * len(df)
        print(f"[DEBUG] [score_batch] Before deduction: user.thesis_quota={user.thesis_quota}, total_fee={total_fee}")
        log_access("DEBUG", f"[score_batch] Before deduction: user.thesis_quota={user.thesis_quota}, total_fee={total_fee}")
        if user.thesis_quota < total_fee:
            print(f"[DEBUG] [score_batch] Insufficient points: current={user.thesis_quota}, required={total_fee}")
            log_access("DEBUG", f"[score_batch] Insufficient points: current={user.thesis_quota}, required={total_fee}")
            flash(f'Insufficient points for batch operation (current: {user.thesis_quota}, required: {total_fee})', 'error')
            return render_template('verify_score_batch_result.html', results=[])
        user.thesis_quota -= total_fee
        db.session.commit()
        print(f"[DEBUG] [score_batch] After deduction: user.thesis_quota={user.thesis_quota}")
        log_access("DEBUG", f"[score_batch] After deduction: user.thesis_quota={user.thesis_quota}")
    else:
        print(f"[DEBUG] [score_batch] No deduction needed for user_role={user_role}")
        log_access("DEBUG", f"[score_batch] No deduction needed for user_role={user_role}")

    results = []
    success_count = 0
    
    for _, row in df.iterrows():
        name = str(row.get('name', '')).strip()
        sid = str(row.get('id', '')).strip()
        if not name or not sid:
            results.append({**row, 'status': 'missing'})
            continue        
        payload = {'name': name, 'id': sid}
        ok = False
        last_data = None
        
        for cfg in cfgs:
            data = _call_api(cfg, payload)
            last_data = data
            
            # 检查是否为有效响应（匹配单个查询的逻辑）
            if data.get('status') in ('y', 'success') or 'gpa' in data:
                # 如果返回了GPA数据但没有status字段，添加成功标志
                if 'gpa' in data and 'status' not in data:
                    data['status'] = 'success'
                    # 确保必要的字段存在
                    if 'id' not in data:
                        data['id'] = sid
                    if 'name' not in data:
                        data['name'] = name
                    if 'major' not in data and 'enroll_year' in data:
                        data['major'] = f"{data.get('enroll_year', '')}-{data.get('graduation_year', '')} student"
                
                # 合并行数据和API返回数据，并标记为成功
                results.append({**row, **data, 'status': 'y'})
                success_count += 1
                ok = True
                break
                
        if not ok:
            # 如果失败，添加最后一个失败的响应数据
            error_result = {**row, 'status': 'fail'}
            if last_data:
                if 'message' in last_data:
                    error_result['error_message'] = last_data['message']
            results.append(error_result)

    # 添加批量操作结果的日志
    log_access("Batch GPA query finished", f"Success: {success_count}/{len(df)}")
    
    session['batch_score'] = results
    return render_template('verify_score_batch_result.html',
                          results=results)


@verifyBP.route('/score/batch/export')
def score_batch_export():
    data = session.get('batch_score')
    if not data:
        flash('No data to export')
        return redirect(url_for('verify.score_query'))
    
    # 处理导出数据
    export_data = []
    for item in data:
        # 复制一份数据，避免修改原始数据
        export_item = item.copy()
        
        # 处理专业字段
        if 'major' not in export_item and 'enroll_year' in export_item:
            export_item['major'] = f"{export_item.get('enroll_year', '')}-{export_item.get('graduation_year', '')} student"
        
        # 添加状态描述
        if export_item.get('status') == 'y':
            export_item['status_desc'] = 'Success'
        elif export_item.get('status') == 'fail':
            export_item['status_desc'] = 'Failed'
        elif export_item.get('status') == 'missing':
            export_item['status_desc'] = 'Incomplete information'
        else:
            export_item['status_desc'] = export_item.get('status', 'Unknown')
        
        export_data.append(export_item)
    
    # 创建DataFrame并导出
    df = pd.DataFrame(export_data)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine='xlsxwriter') as w:
        df.to_excel(w, index=False, sheet_name='GPA Query Result')
    buf.seek(0)
    
    # 记录日志
    log_access("Export batch GPA query result", f"Total {len(data)} records")
    
    return send_file(buf, download_name='GPA_Query_Result.xlsx',
                    as_attachment=True)

# ------------------------------------------------------------
# 6. 论文外部API查询 /verify/thesis_query
# ------------------------------------------------------------
@verifyBP.route('/thesis_query', methods=['GET', 'POST'])
def thesis_query():
    configs = _configs('thesis')  # 获取thesis类型API配置

    # 首次进入页面
    if request.method == 'GET':
        return render_template('thesis_query.html',
                               configs=configs,
                               api_choice='auto',
                               title='')

    # ---------- 自动扣费逻辑 ---------- #
    user_role = session.get('user_role')
    user_id = session.get('user_id')
    user = None
    if user_role == 'teacher':
        from app.models.teacher import Teacher
        user = Teacher.query.get(user_id)
    elif user_role == 'student':
        from app.models.student import Student
        user = Student.query.get(user_id)
    organization = getattr(user, 'organization', None) if user else None
    from app.models.o_convener import OConvener
    convener = OConvener.query.filter_by(org_shortname=organization).first()
    fee = convener.thesis_fee if convener else 0
    print(f"[DEBUG] [thesis_query] user_role={user_role}, user_id={user_id}, organization={organization}, fee={fee}")
    log_access("DEBUG", f"[thesis_query] user_role={user_role}, user_id={user_id}, organization={organization}, fee={fee}")
    if user_role in ('teacher', 'student') and fee > 0:
        print(f"[DEBUG] [thesis_query] user object: {user}")
        log_access("DEBUG", f"[thesis_query] user object: {user}")
        if not hasattr(user, 'thesis_quota') or user.thesis_quota is None:
            print(f"[DEBUG] [thesis_query] user has no thesis_quota, set to 0")
            log_access("DEBUG", f"[thesis_query] user has no thesis_quota, set to 0")
            user.thesis_quota = 0
        print(f"[DEBUG] [thesis_query] Before deduction: user.thesis_quota={user.thesis_quota}, fee={fee}")
        log_access("DEBUG", f"[thesis_query] Before deduction: user.thesis_quota={user.thesis_quota}, fee={fee}")
        if user.thesis_quota < fee:
            print(f"[DEBUG] [thesis_query] Insufficient points: current={user.thesis_quota}, required={fee}")
            log_access("DEBUG", f"[thesis_query] Insufficient points: current={user.thesis_quota}, required={fee}")
            flash(f'Insufficient points (current: {user.thesis_quota}, required: {fee}), operation denied.', 'error')
            return render_template('thesis_query.html',
                                   configs=configs,
                                   api_choice='auto',
                                   title='')
        user.thesis_quota -= fee
        db.session.commit()
        print(f"[DEBUG] [thesis_query] After deduction: user.thesis_quota={user.thesis_quota}")
        log_access("DEBUG", f"[thesis_query] After deduction: user.thesis_quota={user.thesis_quota}")
    else:
        print(f"[DEBUG] [thesis_query] No deduction needed for user_role={user_role}")
        log_access("DEBUG", f"[thesis_query] No deduction needed for user_role={user_role}")

    # 表单取值
    keywords = (request.form.get('title') or '').strip()
    api_choice = request.form.get('api_choice', 'auto')
    print(f"[DEBUG] thesis_query: keywords={keywords}, api_choice={api_choice}")
    log_access("DEBUG", f"thesis_query: keywords={keywords}, api_choice={api_choice}")

    if not keywords:
        flash('Please enter keywords')
        print("[DEBUG] thesis_query: keywords is empty")
        log_access("DEBUG", "thesis_query: keywords is empty")
        return render_template('thesis_query.html',
                               configs=configs,
                               api_choice=api_choice,
                               title=keywords)

    # 构造payload，严格只用keywords字段
    cfg_list = configs if api_choice == 'auto' else [APIConfig.query.get(int(api_choice))]
    payload = {'keywords': keywords}
    print(f"[DEBUG] thesis_query: payload={payload}, cfg_list={[f'{c.base_url}{c.path}' for c in cfg_list]}")
    log_access("DEBUG", f"thesis_query: payload={payload}, cfg_list={[f'{c.base_url}{c.path}' for c in cfg_list]}")

    last_resp, last_cfg = None, None

    # 逐个接口尝试
    for cfg in cfg_list:
        try:
            print(f"[DEBUG] thesis_query: calling API {cfg.base_url}{cfg.path}")
            log_access("DEBUG", f"thesis_query: calling API {cfg.base_url}{cfg.path}")
            data = _call_api(cfg, payload)
            print(f"[DEBUG] thesis_query: API response: {data}")
            log_access("DEBUG", f"thesis_query: API response: {data}")
            last_resp, last_cfg = data, cfg
            # 新增：兼容API直接返回论文列表的情况
            if isinstance(data, list) and data and all(isinstance(x, dict) and 'title' in x and 'abstract' in x for x in data):
                data = {'status': 'success', 'theses': data}
                log_access(f"Thesis external API query", f"Keywords: {keywords}")
                print(f"[DEBUG] thesis_query: success (list), rendering result page")
                return render_template(
                    'thesis_query.html',
                    configs=configs,
                    api_choice=api_choice,
                    title=keywords,
                    source=f'{cfg.service_type} ({cfg.method} {cfg.path})',
                    result=data
                )
            # 兼容output为{"title":..., "abstract":...}的情况
            if (isinstance(data, dict) and data.get('status') in ('y', 'success') and data.get('theses')) or \
               (isinstance(data, dict) and 'title' in data and 'abstract' in data):
                # 如果是单条论文，转为theses列表
                if 'title' in data and 'abstract' in data and 'theses' not in data:
                    data = {'status': 'success', 'theses': [data]}
                log_access(f"Thesis external API query", f"Keywords: {keywords}")
                print(f"[DEBUG] thesis_query: success (dict), rendering result page")
                return render_template(
                    'thesis_query.html',
                    configs=configs,
                    api_choice=api_choice,
                    title=keywords,
                    source=f'{cfg.service_type} ({cfg.method} {cfg.path})',
                    result=data
                )
        except Exception as e:
            print(f"[DEBUG] thesis_query: Exception: {e}")
            log_access("DEBUG", f"thesis_query: Exception: {e}")
            last_resp, last_cfg = {'status': 'error', 'message': str(e)}, cfg
            continue

    # 全部接口均未命中或失败
    print(f"[DEBUG] thesis_query: all API failed, last_resp={last_resp}")
    log_access("DEBUG", f"thesis_query: all API failed, last_resp={last_resp}")
    result = last_resp or {'status': 'not_found'}
    src = f'{last_cfg.service_type} ({last_cfg.method} {last_cfg.path})' if last_cfg else '—'

    return render_template('thesis_query.html',
                           configs=configs,
                           api_choice=api_choice,
                           title=keywords,
                           source=src,
                           result=result)

# ------------------------------------------------------------
# 7. 论文PDF下载 /verify/thesis_download
# ------------------------------------------------------------
@verifyBP.route('/thesis_download', methods=['POST'])
def thesis_download():
    """
    通过外部API下载论文PDF，前端传入title和api_choice。
    input: {"title": ..., "api_choice": ...}
    output: PDF文件流或错误信息
    """
    title = (request.form.get('title') or '').strip()
    api_choice = request.form.get('api_choice', 'auto')
    print(f"[DEBUG] thesis_download: title={title}, api_choice={api_choice}")
    log_access("DEBUG", f"thesis_download: title={title}, api_choice={api_choice}")
    if not title:
        print("[DEBUG] thesis_download: Missing thesis title")
        log_access("DEBUG", "thesis_download: Missing thesis title")
        return {"status": "error", "message": "Missing thesis title"}, 400

    configs = _configs('thesis')
    cfg_list = configs if api_choice == 'auto' else [APIConfig.query.get(int(api_choice))]
    payload = {"title": title}
    last_resp, last_cfg = None, None
    print(f"[DEBUG] thesis_download: payload={payload}, cfg_list={[f'{c.base_url}{c.path}' for c in cfg_list]}")
    log_access("DEBUG", f"thesis_download: payload={payload}, cfg_list={[f'{c.base_url}{c.path}' for c in cfg_list]}")

    for cfg in cfg_list:
        try:
            url = cfg.base_url.rstrip('/') + cfg.path
            # headers = {"Content-Type": "application/json"}
            print(f"[DEBUG] thesis_download: calling API {url}")
            log_access("DEBUG", f"thesis_download: calling API {url}")
            r = requests.get(url, params=payload, timeout=10)
            print(f"[DEBUG] thesis_download: API status={r.status_code}, content-type={r.headers.get('Content-Type')}")
            if r.status_code == 200 and r.headers.get('Content-Type', '').startswith('application/pdf'):
                print(f"[DEBUG] thesis_download: PDF stream received, size={len(r.content)} bytes")
                log_access("DEBUG", f"thesis_download: PDF stream received, size={len(r.content)} bytes")
                return send_file(
                    io.BytesIO(r.content),
                    mimetype='application/pdf',
                    as_attachment=True,
                    download_name=f"{title}.pdf"
                )
            try:
                data = r.json()
                print(f"[DEBUG] thesis_download: API JSON response: {data}")
                log_access("DEBUG", f"thesis_download: API JSON response: {data}")
                last_resp, last_cfg = data, cfg
                if data.get('status') == 'error':
                    print(f"[DEBUG] thesis_download: API returned error: {data.get('message')}")
                    log_access("DEBUG", f"thesis_download: API returned error: {data.get('message')}")
                    continue
                if data.get('pdf_base64'):
                    import base64
                    pdf_bytes = base64.b64decode(data['pdf_base64'])
                    print(f"[DEBUG] thesis_download: Decoded base64 PDF, size={len(pdf_bytes)} bytes")
                    log_access("DEBUG", f"thesis_download: Decoded base64 PDF, size={len(pdf_bytes)} bytes")
                    return send_file(
                        io.BytesIO(pdf_bytes),
                        mimetype='application/pdf',
                        as_attachment=True,
                        download_name=f"{title}.pdf"
                    )
                print(f"[DEBUG] thesis_download: API returned unknown JSON, message={data.get('message')}")
                log_access("DEBUG", f"thesis_download: API returned unknown JSON, message={data.get('message')}")
                return {"status": "error", "message": data.get('message', 'Unknown error')}, 400
            except Exception as e:
                print(f"[DEBUG] thesis_download: API returned non-JSON, error={e}, text={r.text[:200]}")
                log_access("DEBUG", f"thesis_download: API returned non-JSON, error={e}, text={r.text[:200]}")
                return {"status": "error", "message": f"API returned non-PDF, non-JSON response: {r.text[:200]}"}, 400
        except Exception as e:
            print(f"[DEBUG] thesis_download: Exception: {e}")
            log_access("DEBUG", f"thesis_download: Exception: {e}")
            last_resp = {"status": "error", "message": str(e)}
            continue
    print(f"[DEBUG] thesis_download: all API failed, last_resp={last_resp}")
    log_access("DEBUG", f"thesis_download: all API failed, last_resp={last_resp}")
    return last_resp or {"status": "error", "message": "All APIs failed"}, 400

