## import libraries
from app import create_app
from flask_migrate import Migrate
from app.models.base import db

app = create_app()
migrate = Migrate(app, db)

if __name__ == '__main__':
    # 启动应用服务器, 使用默认参数, 开启调试模式
    app.run(debug=True,host='127.0.0.1', port=5000)    
    # app.run(host='0.0.0.0', port=5001)

