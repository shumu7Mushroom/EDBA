from flask import Blueprint, redirect, url_for, render_template

mainBP = Blueprint('main', __name__)

@mainBP.route('/')
def index():
    return render_template('index.html', title="欢迎使用 E-DBA 系统")
