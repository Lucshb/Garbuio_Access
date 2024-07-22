import os
import sqlite3
import logging
from flask import Flask, render_template, request, redirect, url_for, session, send_file
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import pandas as pd
from datetime import datetime
import pytz

app = Flask(__name__)
app.secret_key = 'secretKey'

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

DATABASE = 'logs.db'

def get_db():
    conn = sqlite3.connect(DATABASE)
    return conn

def init_db():
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS user_logs (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            email TEXT NOT NULL,
                            action TEXT NOT NULL,
                            timestamp TEXT NOT NULL
                          )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS app_logs (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            level TEXT NOT NULL,
                            message TEXT NOT NULL,
                            timestamp TEXT NOT NULL
                          )''')
        db.commit()

init_db()

class User(UserMixin):
    def __init__(self, id, email, password, role, dashboards, name):
        self.id = id
        self.email = email
        self.password = password
        self.role = role
        self.dashboards = str(dashboards).split(',')
        self.name = name

def load_users():
    print("Loading users from users.xlsx")
    file_path = os.path.join(os.getcwd(), 'users.xlsx')
    if not os.path.exists(file_path):
        return {}
    df = pd.read_excel(file_path)
    users = {}
    for _, row in df.iterrows():
        users[row['email']] = User(
            row['email'], 
            row['email'], 
            row['password'], 
            row['role'], 
            row['dashboards'], 
            row['name']
        )
    print(f"Users loaded: {list(users.keys())}")
    return users

users = load_users()

@login_manager.user_loader
def load_user(user_id):
    return users.get(user_id)

def log_user_activity(user_email, action):
    db = get_db()
    cursor = db.cursor()
    now = datetime.now(pytz.timezone('America/Sao_Paulo')).strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute('INSERT INTO user_logs (email, action, timestamp) VALUES (?, ?, ?)', (user_email, action, now))
    db.commit()

class SQLiteHandler(logging.Handler):
    def emit(self, record):
        try:
            log_entry = self.format(record)
            db = get_db()
            cursor = db.cursor()
            now = datetime.now(pytz.timezone('America/Sao_Paulo')).strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute('INSERT INTO app_logs (level, message, timestamp) VALUES (?, ?, ?)', 
                           (record.levelname, log_entry, now))
            db.commit()
            print(f"Log inserted: {log_entry}")
        except Exception as e:
            print(f"Error logging to database: {e}")

def setup_logging():
    if not app.debug:
        handler = SQLiteHandler()
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(message)s')
        handler.setFormatter(formatter)
        app.logger.addHandler(handler)

setup_logging()

@app.route('/add_log')
def add_log():
    app.logger.info("Test write to database")
    return "Manual log added"

@app.route('/view_logs')
@login_required
def view_logs():
    if current_user.role != 'admin':
        return 'Access denied', 403
    
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT level, message, timestamp FROM app_logs ORDER BY timestamp DESC')
    logs = cursor.fetchall()
    
    return render_template('view_logs.html', logs=logs)

@app.route('/test_db_write')
def test_db_write():
    try:
        db = get_db()
        cursor = db.cursor()
        now = datetime.now(pytz.timezone('America/Sao_Paulo')).strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute('INSERT INTO app_logs (level, message, timestamp) VALUES (?, ?, ?)', 
                       ("INFO", "Test write to database", now))
        db.commit()
        return "Write successful"
    except Exception as e:
        return f"Write failed: {e}"

@app.route('/download_logs')
@login_required
def download_logs():
    if current_user.role != 'admin':
        return 'Access denied', 403
    
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM app_logs')
    logs = cursor.fetchall()
    
    df = pd.DataFrame(logs, columns=['ID', 'Level', 'Message', 'Timestamp'])
    excel_path = 'logs.xlsx'
    df.to_excel(excel_path, index=False)
    
    return send_file(excel_path, as_attachment=True)

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = users.get(email)
        if user and user.password == password:
            login_user(user)
            session['start_time'] = datetime.now(pytz.timezone('America/Sao_Paulo')).isoformat()
            log_user_activity(user.email, 'login')
            app.logger.info(f"User logged in: {user.email}, Role: {user.role}")
            return redirect(url_for('dashboard'))
        return 'Invalid credentials'
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    print("Dashboard route accessed")  # Debug log
    all_dashboards = [
        {"url": "https://app.powerbi.com/view?r=eyJrIjoiMmU1MTBmYTItMmY3MS00NjYzLTg3ZWUtOWQyYzI1YTgyYTQxIiwidCI6ImNjMmE5NWVhLTMzNWMtNDQzYi04NDQzLWU5YWQzM2ZmOWUwNCJ9", "title": "Central de BIs"},
        {"url": "https://app.powerbi.com/reportEmbed?reportId=196b835a-4b66-4f9d-b7e0-1d63d4f02e88&autoAuth=true&ctid=cc2a95ea-335c-443b-8443-e9ad33ff9e04", "title": "Faturamento"},
        {"url": "https://app.powerbi.com/view?r=eyJrIjoiMTljYjYxOGQtNDMzMy00MTE2LTkxMzYtNmZhMGM1MmMzZjgxIiwidCI6ImNjMmE5NWVhLTMzNWMtNDQzYi04NDQzLWU5YWQzM2ZmOWUwNCJ9", "title": "Controladoria Anderson"},
        {"url": "https://app.powerbi.com/view?r=eyJrIjoiYTIyNGRkZjUtYTBkMS00ZjgxLTgyOWMtOTcxYTc4NjRiMDQ2IiwidCI6ImNjMmE5NWVhLTMzNWMtNDQzYi04NDQzLWU5YWQzM2ZmOWUwNCJ9", "title": "Controladoria Luiz"},
        {"url": "https://app.powerbi.com/view?r=eyJrIjoiMWMxMTEwZWEtODM4ZS00YmM0LThjNzEtMTdkYmUwYWYzODE4IiwidCI6ImNjMmE5NWVhLTMzNWMtNDQzYi04NDQzLWU5YWQzM2ZmOWUwNCJ9", "title": "Controladoria Cesar"},
        {"url": "https://app.powerbi.com/view?r=eyJrIjoiY2RmZWFhYTctNzZjOC00YmVjLThiNTItNWZiMjFkMGJmOWJjIiwidCI6ImNjMmE5NWVhLTMzNWMtNDQzYi04NDQzLWU5YWQzM2ZmOWUwNCJ9", "title": "Controladoria Frederico"},
        {"url": "https://app.powerbi.com/view?r=eyJrIjoiMGM5YzM3MGQtZTkwZi00NzFhLTlkNzYtNmFkNTk4ZGUwODdlIiwidCI6ImNjMmE5NWVhLTMzNWMtNDQzYi04NDQzLWU5YWQzM2ZmOWUwNCJ9", "title": "Controladoria Janaina"},
        {"url": "https://app.powerbi.com/view?r=eyJrIjoiMWEzODYyNDctNTU1NS00OWZlLWE2NGYtZGVmOTM3NjkyMTI1IiwidCI6ImNjMmE5NWVhLTMzNWMtNDQzYi04NDQzLWU5YWQzM2ZmOWUwNCJ9", "title": "Controladoria Anderson"},
        {"url": "https://app.powerbi.com/reportEmbed?reportId=385a53c2-365e-416c-9ca5-f9c3f08bcd11&autoAuth=true&ctid=cc2a95ea-335c-443b-8443-e9ad33ff9e04", "title": "Controladoria Exportável"},
        {"url": "https://app.powerbi.com/view?r=eyJrIjoiZjg0YTQ5OGQtOWI2MC00YWFkLTk3ZmMtYzcyYTMxY2U0YTcyIiwidCI6ImNjMmE5NWVhLTMzNWMtNDQzYi04NDQzLWU5YWQzM2ZmOWUwNCJ9", "title": "Abastecimento"},
        {"url": "https://app.powerbi.com/view?r=eyJrIjoiN2IwYjFhZGUtYWYwNC00NjI2LWFkMGYtMmVjYzE2MTI1ZWM3IiwidCI6ImNjMmE5NWVhLTMzNWMtNDQzYi04NDQzLWU5YWQzM2ZmOWUwNCJ9", "title": "Suprimentos"},
        {"url": "https://app.powerbi.com/view?r=eyJrIjoiOTBlNDlkNmUtMWM1Ni00MWE2LThiMDEtMDIwMmVmNmNjN2RjIiwidCI6ImNjMmE5NWVhLTMzNWMtNDQzYi04NDQzLWU5YWQzM2ZmOWUwNCJ9", "title": "Recursos Humanos"},
        {"url": "https://app.powerbi.com/view?r=eyJrIjoiZDYzODQ2MGYtZjU4NS00Y2M1LWFjZDEtNGViMzIyYjNlZGQwIiwidCI6ImNjMmE5NWVhLTMzNWMtNDQzYi04NDQzLWU5YWQzM2ZmOWUwNCJ9", "title": "Manutenção"},
        {"url": "https://app.powerbi.com/view?r=eyJrIjoiNmMxYzJhNTctYmNkZC00MzVlLWI1ZTMtN2U0NWE2YjYxMjY4IiwidCI6ImNjMmE5NWVhLTMzNWMtNDQzYi04NDQzLWU5YWQzM2ZmOWUwNCJ9", "title": "Contas a Pagar"},
        {"url": "https://app.powerbi.com/view?r=eyJrIjoiYWQxMGYwNTgtZWEwMi00OTg0LTgyZjAtYTI0ZDcwY2NiMzkzIiwidCI6ImNjMmE5NWVhLTMzNWMtNDQzYi04NDQzLWU5YWQzM2ZmOWUwNCJ9", "title": "Pátio"},
    ]
    
    user_dashboards = []
    for db in all_dashboards:
        for user_db in current_user.dashboards:
            if user_db.strip() in db['url']:
                user_dashboards.append(db)
    
    app.logger.info(f"Current user role: {current_user.role}")
    return render_template('dashboard.html', user_dashboards=user_dashboards, user_name=current_user.name, user_role=current_user.role)

@app.route('/logout')
@login_required
def logout():
    try:
        app.logger.info("Logout route accessed")
        start_time_str = session.pop('start_time', None)
        if start_time_str:
            start_time = datetime.fromisoformat(start_time_str)
            session_duration = datetime.now(pytz.timezone('America/Sao_Paulo')) - start_time
            log_user_activity(current_user.email, f'logout (duration: {session_duration})')
        else:
            log_user_activity(current_user.email, 'logout (duration: unknown)')
        logout_user()
        app.logger.info("Logout successful")
        return redirect(url_for('login'))
    except Exception as e:
        app.logger.error(f"Error during logout: {e}")
        return 'Internal Server Error', 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
