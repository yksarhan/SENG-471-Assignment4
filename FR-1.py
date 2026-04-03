from flask import Flask, request, redirect, url_for, session, flash, render_template_string
from flask_bcrypt import Bcrypt
import re

app = Flask(__name__)
app.secret_key = "your-super-secret-key"  # replace with env var in production
bcrypt = Bcrypt(app)

# In-memory store (swap to persistent DB for real app)
users = {}

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

base_template = '''
<!doctype html>
<title>{{ title }}</title>
<h2>{{ title }}</h2>
{% with messages = get_flashed_messages() %}
  {% if messages %}
    <ul style="color:red;">{% for m in messages %}<li>{{ m }}</li>{% endfor %}</ul>
  {% endif %}
{% endwith %}
{{ body|safe }}
'''

@app.route("/")
def home():
    if session.get("user_email"):
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")

        if not email or not password or not confirm:
            flash("All fields are required.")
            return redirect(url_for("register"))

        if not EMAIL_RE.match(email):
            flash("Enter a valid email address.")
            return redirect(url_for("register"))

        if password != confirm:
            flash("Password and confirm password must match.")
            return redirect(url_for("register"))

        if len(password) < 8:
            flash("Password must be at least 8 characters.")
            return redirect(url_for("register"))

        if email in users:
            flash("This email is already registered. Use another email.")
            return redirect(url_for("register"))

        hashed = bcrypt.generate_password_hash(password).decode("utf-8")
        users[email] = {
            "email": email,
            "password_hash": hashed,
            "biometric_enabled": False,
            "social_provider": None,
        }

        flash("Registration successful. Please log in.")
        return redirect(url_for("login"))

    body = '''
<form method="POST">
  Email: <input name="email" type="email" required><br>
  Password: <input name="password" type="password" required><br>
  Confirm Password: <input name="confirm" type="password" required><br>
  <button type="submit">Register</button>
</form>
<p>Already registered? <a href="/login">Login</a></p>
'''
    return render_template_string(base_template, title="Register", body=body)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Email and password are required.")
            return redirect(url_for("login"))

        user = users.get(email)
        if not user or not bcrypt.check_password_hash(user["password_hash"], password):
            flash("Invalid credentials.")
            return redirect(url_for("login"))

        session["user_email"] = email
        flash("Login successful.")
        return redirect(url_for("dashboard"))

    body = '''
<form method="POST">
  Email: <input name="email" type="email" required><br>
  Password: <input name="password" type="password" required><br>
  <button type="submit">Login</button>
</form>
<p>Or login with: <a href="/login/google">Google</a> | <a href="/login/apple">Apple</a></p>
<p>Not registered? <a href="/register">Register</a></p>
<p>Biometric login: <a href="/biometric-login">Use biometric login</a></p>
'''
    return render_template_string(base_template, title="Login", body=body)

@app.route("/login/google")
def login_google():
    # Stub / placeholder for OAuth flow
    if not users:
        flash("No users are registered yet for social login demo.")
        return redirect(url_for("login"))

    # For demo, take first user as social user
    first_email = next(iter(users))
    user = users[first_email]
    user["social_provider"] = "Google"
    session["user_email"] = first_email
    flash("Logged in with Google (demo stub).")
    return redirect(url_for("dashboard"))

@app.route("/login/apple")
def login_apple():
    if not users:
        flash("No users are registered yet for social login demo.")
        return redirect(url_for("login"))

    first_email = next(iter(users))
    user = users[first_email]
    user["social_provider"] = "Apple"
    session["user_email"] = first_email
    flash("Logged in with Apple (demo stub).")
    return redirect(url_for("dashboard"))

@app.route("/dashboard")
def dashboard():
    email = session.get("user_email")
    if not email or email not in users:
        flash("Please log in first.")
        return redirect(url_for("login"))

    user = users[email]
    body = f'''
<p>Welcome, {email}!</p>
<p>Social login provider: {user.get('social_provider', 'None')}</p>
<p>Biometric enabled: {user.get('biometric_enabled')}</p>
<p><a href="/settings">Settings</a> | <a href="/logout">Logout</a></p>
'''
    return render_template_string(base_template, title="Dashboard", body=body)

@app.route("/settings", methods=["GET", "POST"])
def settings():
    email = session.get("user_email")
    if not email or email not in users:
        flash("Please log in first.")
        return redirect(url_for("login"))

    user = users[email]
    if request.method == "POST":
        action = request.form.get("action")
        if action == "enable":
            user["biometric_enabled"] = True
            flash("Biometric authentication enabled.")
        else:
            user["biometric_enabled"] = False
            flash("Biometric authentication disabled.")
        return redirect(url_for("settings"))

    body = f'''
<form method="POST">
  <p>Biometric authentication is currently: {user.get('biometric_enabled')}</p>
  <button name="action" value="enable">Enable Biometric</button>
  <button name="action" value="disable">Disable Biometric</button>
</form>
<p><a href="/dashboard">Back to dashboard</a></p>
'''
    return render_template_string(base_template, title="Settings", body=body)

@app.route("/biometric-login", methods=["GET", "POST"])
def biometric_login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        user = users.get(email)
        if not user:
            flash("User not found for biometric login.")
            return redirect(url_for("biometric_login"))

        if not user.get("biometric_enabled"):
            flash("Biometric is not enabled for this account.")
            return redirect(url_for("login"))

        # Emulated biometric success for supported device
        session["user_email"] = email
        flash("Biometric login successful.")
        return redirect(url_for("dashboard"))

    body = '''
<form method="POST">
  Email: <input name="email" type="email" required><br>
  <button type="submit">Login with Biometric (simulated)</button>
</form>
<p>Set up biometric first in <a href="/settings">Settings</a></p>
'''
    return render_template_string(base_template, title="Biometric Login", body=body)

@app.route("/logout")
def logout():
    session.pop("user_email", None)
    flash("Logged out.")
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True, port=5000)