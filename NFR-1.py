from flask import Flask, request, redirect, url_for, session, flash, render_template_string
from flask_bcrypt import Bcrypt
import time

app = Flask(__name__)
app.secret_key = 'your-secret-key'
bcrypt = Bcrypt(app)

# Mock in-memory user store for demo (replace with DB in prod)
users = {
    'user@example.com': bcrypt.generate_password_hash('Password123').decode('utf-8')
}

login_attempts = {}

BASE_TEMPLATE = '''
<!doctype html>
<title>{{ title }}</title>
<h2>{{ title }}</h2>
{% with messages = get_flashed_messages() %}
  {% if messages %}
    <div style="color: red; margin-bottom: 10px;">{% for m in messages %}<p>{{ m }}</p>{% endfor %}</div>
  {% endif %}
{% endwith %}
{{ body|safe }}
'''

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        start = time.time()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        if not email or not password:
            flash('Please enter both email and password.')
            return redirect(url_for('login'))

        # immediate non-technical feedback
        if email not in users:
            flash('No account found with that email. Did you mean to sign up?')
            _track_attempt(email)
            return redirect(url_for('login'))

        if not bcrypt.check_password_hash(users[email], password):
            flash('Invalid email or password. Please try again.')
            _track_attempt(email)
            return redirect(url_for('login'))

        session['user_email'] = email
        login_attempts.pop(email, None)

        elapsed = time.time() - start
        if elapsed > 5:
            flash('Login took longer than expected; performance is being investigated.')

        return redirect(url_for('dashboard'))

    body = '''
<form method="post">
  Email<br><input type="email" name="email" required><br>
  Password<br><input type="password" name="password" required><br>
  <button type="submit">Login</button>
</form>
<p><a href="/forgot-password">Forgot password?</a></p>
<p><a href="/register">Create account</a></p>
'''
    return render_template_string(BASE_TEMPLATE, title='Sign In', body=body)

@app.route('/dashboard')
def dashboard():
    if not session.get('user_email'):
        flash('Please sign in to continue.')
        return redirect(url_for('login'))
    return render_template_string(BASE_TEMPLATE, title='Dashboard', body=f'<p>Welcome {session["user_email"]}</p>')

@app.route('/forgot-password')
def forgot_password():
    body = '''
<p>If you forgot your password, follow the reset instructions emailed to you.</p>
<p>(This is a placeholder. Implement email reset workflow in production.)</p>
<p><a href="/login">Back to login</a></p>
'''
    return render_template_string(BASE_TEMPLATE, title='Forgot Password', body=body)

def _track_attempt(email):
    now = time.time()
    attempts = login_attempts.get(email, [])
    attempts = [t for t in attempts if now - t < 300]  # keep last 5 minutes
    attempts.append(now)
    login_attempts[email] = attempts

    if len(attempts) >= 3:
        flash('Having trouble signing in? Use "Forgot password" or contact support.')

if __name__ == '__main__':
    app.run(debug=True, port=5000)