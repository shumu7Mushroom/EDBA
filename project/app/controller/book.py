
from flask import Blueprint,render_template, request
from app.models.base import db
from app.models.book import Book

bookBP = Blueprint('book',__name__)

@bookBP.route('', methods=['GET'])
def get_book():
    with db.auto_commit():
        book = Book()
        book.title = 'aaa'
        book.author = 'aaa'
        book.binding = 'aaa'
        book.publisher = 'aaa'
        book.price = "100"
        book.pages = 1000
        book.pubdate = 'aaa'
        book.isbn = 'aaa'
        book.summary = 'aaa'
        book.image = 'aaa'
        # 数据库的insert操作
        db.session.add(book)
    
    return 'hello book'