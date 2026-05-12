import sqlite3

conn = sqlite3.connect('pipeline_state/pipeline.db')
with open('scripts/init_db.sql', 'r') as f:
    sql = f.read()
conn.executescript(sql)
conn.close()
print('Database initialized.')