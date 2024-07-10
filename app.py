import os
from flask import Flask, render_template, request, redirect, url_for, g, session
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import pandas as pd
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'secretKey'

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, id, email, password, role, dashboards, name):
        self.id = id
        self.email = email
        self.password = password
        self.role = role
        self.dashboards = dashboards
        self.name = name

def load_users():
    df = pd.read_excel('users.xlsx')
    users = {}
    for _, row in df.iterrows():
        users[row['email']] = User(row['email'], row['email'], row['password'], row['role'], row['dashboards'], row['name'])
    return users

users = load_users()

@login_manager.user_loader
def load_user(user_id):
    return users.get(user_id)

# Função para registrar logs no Excel
def log_user_activity(user_email, action):
    log_file = 'user_logs.xlsx'
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    try:
        df = pd.read_excel(log_file)
    except FileNotFoundError:
        df = pd.DataFrame(columns=['email', 'action', 'timestamp'])

    new_log = pd.DataFrame([[user_email, action, now]], columns=['email', 'action', 'timestamp'])
    df = pd.concat([df, new_log], ignore_index=True)
    df.to_excel(log_file, index=False)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = users.get(email)
        if user and user.password == password:
            login_user(user)
            session['start_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # Inicializa o start_time no login
            log_user_activity(user.email, 'login')  # Registra o login
            return redirect(url_for('dashboard'))
        return 'Invalid credentials'
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    dashboards = current_user.dashboards.split(',')
    titles = ["Abastecimento", "Suprimentos"]  # Títulos específicos para os dashboards
    return render_template('templates/dashboard.html', dashboards=dashboards, titles=titles, user_name=current_user.name, zip=zip)

@app.route('/logout')
@login_required
def logout():
    start_time_str = session.pop('start_time', None)
    if start_time_str:
        start_time = datetime.strptime(start_time_str, '%Y-%m-%d %H:%M:%S')
        session_duration = datetime.now() - start_time
        log_user_activity(current_user.email, f'logout (duration: {session_duration})')  # Registra o logout com duração
    else:
        log_user_activity(current_user.email, 'logout (duration: unknown)')
    logout_user()
    return redirect(url_for('login'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
