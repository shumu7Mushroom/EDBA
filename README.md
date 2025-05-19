# EDBA

# Requirements

# How to use

You need to add a secure.py file in project/app/config before starts, below is a sample

```python
import os, sys

print("Loading secure.py from:", __file__)
UPLOAD_FOLDER = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        '..', '..', '..',
        'uploads'
    )
)
print("Configured UPLOAD_FOLDER =", UPLOAD_FOLDER)

SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:@localhost:3306/edba_db?charset=utf8mb4'
SQLALCHEMY_TRACK_MODIFICATIONS = False

MAIL_SERVER = ''
MAIL_PORT = ''
MAIL_USE_SSL = True
MAIL_USERNAME = ''
MAIL_PASSWORD = ''
MAIL_DEFAULT_SENDER = ''
```

Then run

```bash
python teamwork.py
```
