# 📁 app/controller/verify.py
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
    """当前 O‑Convener 配置的接口列表"""
    q = APIConfig.query.filter_by(institution_id=session.get('user_id'))
    if service_type:
        q = q.filter_by(service_type=service_type)
    return q.all()

# app/controller/verify.py
def _call_api(cfg, payload, files=None):
    """
    根据 cfg 调用外部接口
    - 无文件:  application/json (默认) 或 application/x-www-form-urlencoded
    - 有文件:  multipart/form-data
    """
    url = cfg.base_url.rstrip('/') + cfg.path
    try:
        # 检查是否为特定路径，使用不同的方式发送请求
        use_json = '/student/record' in cfg.path
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
    cfg = APIConfig.query.filter_by(institution_id=inst_id,
                                    service_type=service_type).first()

    if request.method == 'POST':
        base_url = request.form.get('base_url', '').strip()
        path     = request.form.get('path', '').strip()
        method   = request.form.get('method', 'POST').upper()
        if cfg:
            cfg.base_url, cfg.path, cfg.method = base_url, path, method
        else:
            cfg = APIConfig(institution_id=inst_id,
                            service_type=service_type,
                            base_url=base_url, path=path, method=method)
            db.session.add(cfg)
        db.session.commit()
        flash('Saved successfully!')

    return render_template('api_config_form.html',
                           cfg=cfg, service_type=service_type)

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
        # 直接回渲染页面而非 redirect，避免丢失输入
        return render_template('verify_identity.html',
                               configs=configs,
                               api_choice=api_choice,
                               name=name,
                               stu_id=sid)

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
            # 外部接口成功标志
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
