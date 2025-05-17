"""
脚本用于删除api_config表中的唯一约束，允许同一机构的同一服务类型有多个API配置
"""
from app.models.base import db
from app import create_app
import pymysql

app = create_app()

with app.app_context():
    try:
        # 创建直接连接
        conn = pymysql.connect(
            host=app.config.get('MYSQL_HOST', 'localhost'),
            user=app.config.get('MYSQL_USER', 'root'),
            password=app.config.get('MYSQL_PASSWORD', ''),
            database=app.config.get('MYSQL_DB', 'edba')
        )
        
        with conn.cursor() as cursor:
            # 检查约束是否存在
            cursor.execute("""
                SELECT CONSTRAINT_NAME
                FROM information_schema.TABLE_CONSTRAINTS
                WHERE CONSTRAINT_SCHEMA = %s
                AND TABLE_NAME = 'api_config'
                AND CONSTRAINT_NAME = 'uk_inst_service'
            """, (app.config.get('MYSQL_DB', 'edba')))
            
            constraint_exists = cursor.fetchone()
            
            if constraint_exists:
                print("找到唯一约束 'uk_inst_service'，正在删除...")
                # 删除唯一约束
                cursor.execute("ALTER TABLE api_config DROP INDEX uk_inst_service")
                conn.commit()
                print("成功删除唯一约束 'uk_inst_service'")
            else:
                print("未找到唯一约束 'uk_inst_service'，无需操作")
            
            # 验证约束已被删除
            cursor.execute("""
                SELECT CONSTRAINT_NAME
                FROM information_schema.TABLE_CONSTRAINTS
                WHERE CONSTRAINT_SCHEMA = %s
                AND TABLE_NAME = 'api_config'
                AND CONSTRAINT_NAME = 'uk_inst_service'
            """, (app.config.get('MYSQL_DB', 'edba')))
            
            if not cursor.fetchone():
                print("验证通过：约束已被成功删除")
            else:
                print("警告：约束仍然存在，请检查是否有权限问题")
        
    except Exception as e:
        print(f"执行过程中出现错误: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

print("脚本执行完成")
