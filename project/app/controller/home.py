from flask import Blueprint, redirect, url_for, render_template
from app.models.rule import Rule

mainBP = Blueprint('main', __name__)

@mainBP.route('/')
def index():
    return render_template('index.html', title="欢迎使用 E-DBA 系统")

@mainBP.route('/rules/view')
def view_rules():
    rules = Rule.query.all()
    return render_template('view_rules.html', rules=rules)
