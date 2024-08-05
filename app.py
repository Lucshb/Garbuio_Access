import os
import sqlite3
import io
import shutil
from flask import Flask, render_template, request, redirect, url_for, session, send_file
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import pandas as pd
import xlsxwriter
from datetime import datetime, timedelta
import pytz

app = Flask(__name__)
app.secret_key = 'secretKey'

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

DATABASE = os.path.join(os.getcwd(), 'logs.db')
BACKUP_FOLDER = os.path.join(os.getcwd(), 'backups')

if not os.path.exists(BACKUP_FOLDER):
    os.makedirs(BACKUP_FOLDER)

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

def backup_logs():
    now = datetime.now(pytz.timezone('America/Sao_Paulo'))
    backup_file = os.path.join(BACKUP_FOLDER, f'logs_backup_{now.strftime("%Y%m%d_%H%M%S")}.db')
    shutil.copy(DATABASE, backup_file)
    print(f'Backup created: {backup_file}')

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/test')
def test():
    return "Test route is working!"

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
            print(f"User logged in: {user.email}, Role: {user.role}")
            return redirect(url_for('dashboard'))
        return 'Invalid credentials'
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    all_dashboards = [
        {"url": "https://app.powerbi.com/view?r=eyJrIjoiMmU1MTBmYTItMmY3MS00NjYzLTg3ZWUtOWQyYzI1YTgyYTQxIiwidCI6ImNjMmE5NWVhLTMzNWMtNDQzYi04NDQzLWU5YWQzM2ZmOWUwNCJ9&chromeless=true", "title": "Central de BIs"},
        {"url": "https://app.powerbi.com/view?r=eyJrIjoiNTBjZGYxZDMtOGUzNy00OTBjLWI1NTQtNjAxM2QyOWMzMDkyIiwidCI6ImNjMmE5NWVhLTMzNWMtNDQzYi04NDQzLWU5YWQzM2ZmOWUwNCJ9&chromeless=true", "title": "Faturamento"},
        {"url": "https://app.powerbi.com/view?r=eyJrIjoiZmYzYTI4MWItMjYyNS00NWNmLTllYTUtODk5NDliYTJjMzc1IiwidCI6ImNjMmE5NWVhLTMzNWMtNDQzYi04NDQzLWU5YWQzM2ZmOWUwNCJ9&chromeless=true", "title": "Controladoria Marina"},
        {"url": "https://app.powerbi.com/view?r=eyJrIjoiMTljYjYxOGQtNDMzMy00MTE2LTkxMzYtNmZhMGM1MmMzZjgxIiwidCI6ImNjMmE5NWVhLTMzNWMtNDQzYi04NDQzLWU5YWQzM2ZmOWUwNCJ9&chromeless=true", "title": "Controladoria Anderson"},
        {"url": "https://app.powerbi.com/view?r=eyJrIjoiYTIyNGRkZjUtYTBkMS00ZjgxLTgyOWMtOTcxYTc4NjRiMDQ2IiwidCI6ImNjMmE5NWVhLTMzNWMtNDQzYi04NDQzLWU5YWQzM2ZmOWUwNCJ9&chromeless=true", "title": "Controladoria Luiz"},
        {"url": "https://app.powerbi.com/view?r=eyJrIjoiMWMxMTEwZWEtODM4ZS00YmM0LThjNzEtMTdkYmUwYWYzODE4IiwidCI6ImNjMmE5NWVhLTMzNWMtNDQzYi04NDQzLWU5YWQzM2ZmOWUwNCJ9&chromeless=true", "title": "Controladoria Cesar"},
        {"url": "https://app.powerbi.com/view?r=eyJrIjoiY2RmZWFhYTctNzZjOC00YmVjLThiNTItNWZiMjFkMGJmOWJjIiwidCI6ImNjMmE5NWVhLTMzNWMtNDQzYi04NDQzLWU5YWQzM2ZmOWUwNCJ9&chromeless=true", "title": "Controladoria Frederico"},
        {"url": "https://app.powerbi.com/view?r=eyJrIjoiMGM5YzM3MGQtZTkwZi00NzFhLTlkNzYtNmFkNTk4ZGUwODdlIiwidCI6ImNjMmE5NWVhLTMzNWMtNDQzYi04NDQzLWU5YWQzM2ZmOWUwNCJ9&chromeless=true", "title": "Controladoria Janaina"},
        {"url": "https://app.powerbi.com/reportEmbed?reportId=385a53c2-365e-416c-9ca5-f9c3f08bcd11&autoAuth=true&ctid=cc2a95ea-335c-443b-8443-e9ad33ff9e04", "title": "Controladoria Exportável"},
        {"url": "https://app.powerbi.com/view?r=eyJrIjoiZjg0YTQ5OGQtOWI2MC00YWFkLTk3ZmMtYzcyYTMxY2U0YTcyIiwidCI6ImNjMmE5NWVhLTMzNWMtNDQzYi04NDQzLWU5YWQzM2ZmOWUwNCJ9&chromeless=true", "title": "Abastecimento"},
        {"url": "https://app.powerbi.com/view?r=eyJrIjoiN2IwYjFhZGUtYWYwNC00NjI2LWFkMGYtMmVjYzE2MTI1ZWM3IiwidCI6ImNjMmE5NWVhLTMzNWMtNDQzYi04NDQzLWU5YWQzM2ZmOWUwNCJ9&chromeless=true", "title": "Suprimentos"},
        {"url": "https://app.powerbi.com/view?r=eyJrIjoiOTBlNDlkNmUtMWM1Ni00MWE2LThiMDEtMDIwMmVmNmNjN2RjIiwidCI6ImNjMmE5NWVhLTMzNWMtNDQzYi04NDQzLWU5YWQzM2ZmOWUwNCJ9&chromeless=true", "title": "Recursos Humanos"},
        {"url": "https://app.powerbi.com/view?r=eyJrIjoiZDYzODQ2MGYtZjU4NS00Y2M1LWFjZDEtNGViMzIyYjNlZGQwIiwidCI6ImNjMmE5NWVhLTMzNWMtNDQzYi04NDQzLWU5YWQzM2ZmOWUwNCJ9&chromeless=true", "title": "Manutenção"},
        {"url": "https://app.powerbi.com/view?r=eyJrIjoiNmMxYzJhNTctYmNkZC00MzVlLWI1ZTMtN2U0NWE2YjYxMjY4IiwidCI6ImNjMmE5NWVhLTMzNWMtNDQzYi04NDQzLWU5YWQzM2ZmOWUwNCJ9&chromeless=true", "title": "Contas a Pagar"},
        {"url": "https://app.powerbi.com/view?r=eyJrIjoiYWQxMGYwNTgtZWEwMi00OTg0LTgyZjAtYTI0ZDcwY2NiMzkzIiwidCI6ImNjMmE5NWVhLTMzNWMtNDQzYi04NDQzLWU5YWQzM2ZmOWUwNCJ9&chromeless=true", "title": "Pátio"},
    ]

    user_dashboards = []
    for db in all_dashboards:
        for user_db in current_user.dashboards:
            if user_db.strip() in db['url']:
                user_dashboards.append(db)
    
    print(f"Current user role: {current_user.role}")
    return render_template('dashboard.html', user_dashboards=user_dashboards, user_name=current_user.name, user_role=current_user.role)

@app.route('/logout')
@login_required
def logout():
    try:
        print("Logout route accessed")
        start_time_str = session.pop('start_time', None)
        if start_time_str:
            start_time = datetime.fromisoformat(start_time_str)
            session_duration = datetime.now(pytz.timezone('America/Sao_Paulo')) - start_time
            log_user_activity(current_user.email, f'logout (duration: {session_duration})')
        else:
            log_user_activity(current_user.email, 'logout (duration: unknown)')
        logout_user()
        print("Logout successful")
        return redirect(url_for('login'))
    except Exception as e:
        print(f"Error during logout: {e}")
        return 'Internal Server Error', 500

@app.route('/download_logs')
@login_required
def download_logs():
    if current_user.role == 'admin':
        db = get_db()
        cursor = db.cursor()
        cursor.execute('SELECT email, action, timestamp FROM user_logs')
        logs = cursor.fetchall()

        if not logs:
            return 'No logs found'

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet()

        worksheet.write(0, 0, 'Email')
        worksheet.write(0, 1, 'Action')
        worksheet.write(0, 2, 'Timestamp')

        for row_num, log in enumerate(logs, 1):
            worksheet.write(row_num, 0, log[0])
            worksheet.write(row_num, 1, log[1])
            worksheet.write(row_num, 2, log[2])

        workbook.close()
        output.seek(0)

        return send_file(output, as_attachment=True, download_name='logs.xlsx')
    return 'Access denied', 403

if __name__ == '__main__':
    # Configurar backup regular dos logs
    backup_logs()  # Executa um backup na inicialização
    app.before_first_request(backup_logs)  # Configura um backup antes da primeira requisição
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
