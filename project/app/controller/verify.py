# 📁 app/controller/verify.py
from flask import (
    Blueprint, render_template, request, session,
    redirect, url_for, flash, send_file
)
import io, json, requests, pandas as pd
from app.models.api_config import APIConfig
from app.models.base import db

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
    - 无文件:  application/x-www-form-urlencoded
    - 有文件:  multipart/form-data
    """
    url = cfg.base_url.rstrip('/') + cfg.path
    if cfg.method.lower() == 'post':
        if files:                                   # 带照片
            r = requests.post(url, data=payload, files=files, timeout=5)
        else:                                       # 纯表单
            r = requests.post(url, data=payload, timeout=5)
    else:                                           # GET
        r = requests.get(url, params=payload, timeout=5)

    r.raise_for_status()        # 4xx/5xx 直接抛异常
    return r.json()




# ------------------------------------------------------------
# 1. 接口配置  /verify/config/<service_type>
# ------------------------------------------------------------
@verifyBP.route('/config/<service_type>', methods=['GET', 'POST'])
def api_config_form(service_type):
    if not _must_convener():
        return '只有 O‑Convener 可以配置接口', 403

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
        flash('保存成功！')

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
        flash('姓名 / 学号 不能为空')
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
        return '请上传 Excel 文件', 400
    df = pd.read_excel(file)

    cfgs = _configs('identity')
    if not cfgs:
        return '未配置任何认证接口', 400

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
        return '暂无数据可导出', 400
    df = pd.DataFrame(data)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine='xlsxwriter') as w:
        df.to_excel(w, index=False, sheet_name='result')
    buf.seek(0)
    return send_file(buf, download_name='identity_batch.xlsx',
                     as_attachment=True)
