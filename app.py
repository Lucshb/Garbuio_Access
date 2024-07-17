import os
import sqlite3
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
            session['start_time'] = datetime.now(pytz.timezone('America/Sao_Paulo')).strftime('%Y-%m-%d %H:%M:%S')
            log_user_activity(user.email, 'login')
            print(f"User logged in: {user.email}, Role: {user.role}")
            return redirect(url_for('dashboard'))
        return 'Invalid credentials'
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    print("Dashboard route accessed")  # Debug log
    all_dashboards = [
        {"url": "https://app.powerbi.com/view?r=eyJrIjoiMmU1MTBmYTItMmY3MS00NjYzLTg3ZWUtOWQyYzI1YTgyYTQxIiwidCI6ImNjMmE5NWVhLTMzNWMtNDQzYi04NDQzLWU5YWQzM2ZmOWUwNCJ9", "title": "Central de BIs"},
        {"url": "https://app.powerbi.com/reportEmbed?reportId=8a3852c1-cf03-44ee-a732-1c9893f9041d&autoAuth=true&ctid=cc2a95ea-335c-443b-8443-e9ad33ff9e04", "title": "Faturamento"},
        {"url": "https://app.powerbi.com/view?r=eyJrIjoiMTljYjYxOGQtNDMzMy00MTE2LTkxMzYtNmZhMGM1MmMzZjgxIiwidCI6ImNjMmE5NWVhLTMzNWMtNDQzYi04NDQzLWU5YWQzM2ZmOWUwNCJ9", "title": "Controladoria Anderson"},
        {"url": "https://app.powerbi.com/view?r=eyJrIjoiYTIyNGRkZjUtYTBkMS00ZjgxLTgyOWMtOTcxYTc4NjRiMDQ2IiwidCI6ImNjMmE5NWVhLTMzNWMtNDQzYi04NDQzLWU5YWQzM2ZmOWUwNCJ9", "title": "Controladoria Luiz"},
        {"url": "https://app.powerbi.com/view?r=eyJrIjoiMWMxMTEwZWEtODM4ZS00YmM0LThjNzEtMTdkYmUwYWYzODE4IiwidCI6ImNjMmE5NWVhLTMzNWMtNDQzYi04NDQzLWU5YWQzM2ZmOWUwNCJ9", "title": "Controladoria Cesar"},
        {"url": "https://app.powerbi.com/view?r=eyJrIjoiY2RmZWFhYTctNzZjOC00YmVjLThiNTItNWZiMjFkMGJmOWJjIiwidCI6ImNjMmE5NWVhLTMzNWMtNDQzYi04NDQzLWU5YWQzM2ZmOWUwNCJ9", "title": "Controladoria Frederico"},
        {"url": "https://app.powerbi.com/view?r=eyJrIjoiMGM5YzM3MGQtZTkwZi00NzFhLTlkNzYtNmFkNTk4ZGUwODdlIiwidCI6ImNjMmE5NWVhLTMzNWMtNDQzYi04NDQzLWU5YWQzM2ZmOWUwNCJ9", "title": "Controladoria Janaina"},
        {"url": "https://app.powerbi.com/view?r=eyJrIjoiMWEzODYyNDctNTU1NS00OWZlLWE2NGYtZGVmOTM3NjkyMTI1IiwidCI6ImNjMmE5NWVhLTMzNWMtNDQzYi04NDQzLWU5YWQzM2ZmOWUwNCJ9", "title": "Controladoria Rafael"},
        {"url": "https://app.powerbi.com/reportEmbed?reportId=385a53c2-365e-416c-9ca5-f9c3f08bcd11&autoAuth=true&ctid=cc2a95ea-335c-443b-8443-e9ad33ff9e04", "title": "Controladoria Exportável"},
        {"url": "https://app.powerbi.com/reportEmbed?reportId=0ba6b5ca-c1a0-44b6-9033-db6491ca6f36&autoAuth=true&ctid=cc2a95ea-335c-443b-8443-e9ad33ff9e04", "title": "Abastecimento"},
        {"url": "https://app.powerbi.com/reportEmbed?reportId=c84a7784-b70a-4a52-8ba8-098381066e82&autoAuth=true&ctid=cc2a95ea-335c-443b-8443-e9ad33ff9e04", "title": "Suprimentos"},
        {"url": "https://app.powerbi.com/reportEmbed?reportId=2cccbc6d-b005-4c1d-8a44-044289eca7b5&autoAuth=true&ctid=cc2a95ea-335c-443b-8443-e9ad33ff9e04", "title": "Recursos Humanos"},
        {"url": "https://app.powerbi.com/reportEmbed?reportId=2b57c4a9-f624-4e18-99a4-9350ae5ee0df&autoAuth=true&ctid=cc2a95ea-335c-443b-8443-e9ad33ff9e04", "title": "Manutenção"},
        {"url": "https://app.powerbi.com/reportEmbed?reportId=192565df-af8d-4e7e-bf7b-d5ca570095b4&autoAuth=true&ctid=cc2a95ea-335c-443b-8443-e9ad33ff9e04", "title": "Contas a Pagar"},
        {"url": "https://app.powerbi.com/reportEmbed?reportId=93939e7b-780a-486c-b40d-22dee554aef1&autoAuth=true&ctid=cc2a95ea-335c-443b-8443-e9ad33ff9e04", "title": "Pátio"},
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
            start_time = datetime.strptime(start_time_str, '%Y-%m-%d %H:%M:%S')
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
        return send_file(DATABASE, as_attachment=True)
    return 'Access denied', 403

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
