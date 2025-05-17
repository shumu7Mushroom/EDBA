from sqlalchemy.exc import IntegrityError
from app.models.E_admin import EAdmin
from app.models.Senior_E_Admin import SeniorEAdmin

def create_admin_account(name, email, password, role):
    """
    创建 E-Admin 或 Senior E-Admin 账户，密码以明文存储（不加密）
    """
    from app.models.base import db  # 延迟导入防止循环依赖

    if role not in ("EAdmin", "SeniorEAdmin"):
        return {"error": "Invalid role specified"}

    try:
        if role == "EAdmin":
            admin = EAdmin(name=name, email=email, _password=password)  # 明文密码存储
        else:
            admin = SeniorEAdmin(name=name, email=email, _password=password)  # 明文密码存储

        db.session.add(admin)
        db.session.commit()

        return {"success": True, "admin_id": admin.id, "role": role}
    except IntegrityError:
        db.session.rollback()
        return {"error": "Email already exists"}
    except Exception as e:
        db.session.rollback()
        return {"error": str(e)}
