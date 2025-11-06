import app.db as db
import os
import sqlite3

print('SQLITE_URL ->', db.SQLITE_URL)
path = db.SQLITE_URL.replace('sqlite:///','')
print('db path ->', path)
print('exists ->', os.path.exists(path))
try:
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
    print('tables ->', cur.fetchall())
    conn.close()
except Exception as e:
    print('error ->', e)
