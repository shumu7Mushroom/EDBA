from flask import Flask, render_template, request, session, redirect, url_for, flash
from flask_mail import Mail
from flask_migrate import Migrate
from flask import Blueprint
import os
from app.controller import book, student, teacher, user, admin, oconvener, log, verify, home, senior_admin, t_admin, course, help

from app.models.base import db
from app.models.bank_config import BankConfig

mail = Mail()

# Define the method to register blueprints
def register_blueprints(app):
    app.register_blueprint(book.bookBP,url_prefix='/book')
    app.register_blueprint(student.studentBP,url_prefix='/student')
    app.register_blueprint(teacher.teacherBP,url_prefix='/teacher')
    app.register_blueprint(user.userBP,url_prefix='/user')
    app.register_blueprint(admin.adminBP,url_prefix='/admin')
    app.register_blueprint(senior_admin.senioradminBP,url_prefix='/senioradmin')    
    app.register_blueprint(oconvener.oconvenerBP, url_prefix='/oconvener')
    app.register_blueprint(log.logBP, url_prefix='/log')    
    app.register_blueprint(verify.verifyBP, url_prefix='/verify')
    app.register_blueprint(home.mainBP,url_prefix='')
    app.register_blueprint(t_admin.tadminBP,url_prefix='/tadmin')
    app.register_blueprint(course.courseBP,url_prefix='/course')
    app.register_blueprint(help.helpBP, url_prefix='/help')
    app.register_blueprint(bankConfigBP, url_prefix='/bank_config')

# Register plugins (database association)
def register_plugin(app):
    db.init_app(app)
    Migrate(app, db)
    mail.init_app(app)
    with app.app_context():
        db.create_all()

def register_filters(app):
    app.jinja_env.filters['basename'] = lambda path: os.path.basename(path)

def create_app():
    app = Flask(__name__)
    # app.config.from_object('app.config.setting') # Basic configuration (setting.py) 
    app.config.from_object('app.config.secure') # Important parameter configuration (secure.py)

    # Add secret_key
    app.secret_key = 'a-very-secret-key'  # Can be anything, should be more secure for production
    
    register_filters(app)

    # Register blueprints and associate them with the app object
    register_blueprints(app)
    # Register plugins (database) and associate them with the app object
    register_plugin(app)
    # Remember to return the app
    return app

# Define the bank configuration blueprint
bankConfigBP = Blueprint('bank_config', __name__)

@bankConfigBP.route('/api', methods=['GET', 'POST'])
def bank_api_config():
    if session.get('user_role') != 'convener':
        return redirect(url_for('main.index'))
        
    # Get the current user ID
    user_id = session.get('user_id')
    
    if request.method == 'POST':
        # Find existing configuration based on user_id
        config = BankConfig.query.filter_by(user_id=user_id).first()
        
        if not config:
            # If no corresponding configuration is found, create a new configuration
            config = BankConfig()
            config.user_id = user_id  # Set user_id
        
        # Save basic API configuration
        config.base_url = request.form.get('base_url', '').strip()
        config.auth_path = request.form.get('auth_path', '').strip()
        config.transfer_path = request.form.get('transfer_path', '').strip()
        
        # Save o-convener API configuration
        config.bank_name = request.form.get('bank', '').strip()
        config.account_name = request.form.get('account_name', '').strip()
        config.bank_account = request.form.get('account_number', '').strip()
        config.bank_password = request.form.get('password', '').strip()
        
        # Save input template to api_config
        config.api_config = {
            'input_template': {
                'bank': request.form.get('bank'),
                'account_name': request.form.get('account_name'),
                'account_number': request.form.get('account_number'),
                'password': request.form.get('password')
            }
        }
        
        try:
            db.session.add(config)
            db.session.commit()
            flash('Bank API configuration has been added/updated', 'success')
            return redirect(url_for('oconvener.pay_fee'))
        except Exception as e:
            db.session.rollback()
            print(f"Error saving config: {str(e)}")  # Add debug log
            flash(f'Failed to save configuration: {str(e)}', 'error')
    
    # For GET requests, try to get the current user's existing configuration
    config = BankConfig.query.filter_by(user_id=user_id).first()
    return render_template('bank_api_config.html', config=config)