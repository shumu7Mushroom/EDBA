import json, copy, re

_PLACEHOLDER = re.compile(r'{{\s*(\w+)\s*}}')

def build_payload(template_json: dict, user_data: dict):
    """
    把模板里的 {{name}} / {{id}} / {{photo}} 等占位符
    用用户输入替换，返回真正要提交的 payload(dict)。
    """
    def _walk(obj):
        if isinstance(obj, dict):
            return {k: _walk(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_walk(v) for v in obj]
        if isinstance(obj, str):
            # str 里若出现 {{xxx}} 就替换
            def repl(m): return str(user_data.get(m.group(1), ""))
            return _PLACEHOLDER.sub(repl, obj)
        return obj  # int / bool / None
    return _walk(copy.deepcopy(template_json))
