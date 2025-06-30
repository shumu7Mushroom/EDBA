# EDBA

# Introduction

This repository is just a course project. **NO VALUE AT ALL !!!**

<span style="font-size: 12px; color: #888;">Unless you are a UIC(BNBU) CS student (maybe work?)</span>

# Requirements

Clone the project

```bash
git clone https://github.com/shumu7Mushroom/EDBA.git
```

Create environment using

```bash
conda create --name edba python==3.12
conda activate edba
```

Pip install the requirements library

```bash
cd EDBA
pip install -r requirements.txt
```

It's pity that the requirements.txt maybe not cover all libraries we used after iterations, so if meet some lack of libraries, please pip the lack ones.

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

After that, you need to start your localdatabase (here we use xampp) and create a database name "edba_db"

Then run

```bash
python teamwork.py
```
