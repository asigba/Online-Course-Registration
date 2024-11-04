from datetime import datetime, timezone
from flask import flash, Flask, redirect, render_template, request, url_for
from flask_bcrypt import Bcrypt
from flask_login import login_required, login_user, logout_user, LoginManager, UserMixin
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from pathlib import Path
from random import randint
from wtforms import PasswordField, StringField, SubmitField
from wtforms.validators import InputRequired, Length, ValidationError

# paths to account for package directory structure (see README)
parent_directory = Path(__file__).resolve().parent.parent
database_path = parent_directory / 'database'
database_file_path = Path(f"{database_path}/database.db")
templates_path = 'templates'

# Application
app = Flask(__name__, template_folder=templates_path)
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{database_file_path}"
app.config['SECRET_KEY'] = 'umgccmsc495'

# Database
db = SQLAlchemy(app)

# Encryption for Password Storage
bcrypt = Bcrypt(app)

# Login Manager
login_mgr = LoginManager()
login_mgr.init_app(app)
login_mgr.login_view = "login"
#
@login_mgr.user_loader
def load_user(id):
    return User.query.get(int(id))

# Default Database Table : User
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(30), nullable=False, unique=True)
    password = db.Column(db.String(80), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, onupdate=datetime.now(timezone.utc), nullable=True)     

    # Changing the default representation
    def __repr__(self):
        return f'{self.username}'

# Default Database Table : Student
class Student(db.Model):
    id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    student_id = db.Column(db.Integer, unique=True, nullable=False)
    first_name = db.Column(db.String(30), nullable=False)
    last_name = db.Column(db.String(30), nullable=False)
    updated_at = db.Column(db.DateTime, onupdate=datetime.now(timezone.utc), nullable=True)

    # Establishing a relationship to the User class
    user = db.relationship('User', backref='students')

    def __init__(self, first_name, last_name, id):
        self.id = id
        self.first_name = first_name.lower()
        self.last_name = last_name.lower()
        self.student_id = self.generate_student_id()

    def __repr__(self):
        return f'<Student {self.first_name} {self.last_name}, User ID: {self.student_id}>'
    
    @staticmethod
    def generate_student_id():
        while True:
            # Generate a random 8-digit integer
            unique_id = randint(10000000, 99999999)
            # Check if it already exists in the database
            if not Student.query.filter_by(student_id=unique_id).first():
                return unique_id

class RegisterForm(FlaskForm):
    username = StringField(validators=[InputRequired(), Length(min=4, max=20)],
                           render_kw={"placeholder": "Username"})
    password = PasswordField(validators=[InputRequired(), Length(min=12, max=24)],
                           render_kw={"placeholder": "Password"})
    first_name = StringField(validators=[InputRequired(), Length(min=2, max=63)],
                           render_kw={"placeholder": "First Name"})
    last_name = StringField(validators=[InputRequired(), Length(min=2, max=63)],
                           render_kw={"placeholder": "Last Name"})
    submit = SubmitField("Register")

    def validate_username(self, username):
        existing_user = User.query.filter_by(username=username.data).first()
        if existing_user:
                raise ValidationError(f"Existing account found for username: {existing_user.username}.")


class LoginForm(FlaskForm):
    username = StringField(validators=[InputRequired(), Length(min=4, max=20)],
                           render_kw={"placeholder": "Username"})
    password = PasswordField(validators=[InputRequired(), Length(min=4, max=20)],
                           render_kw={"placeholder": "Password"})
    submit = SubmitField("Login")


class DatabaseInitializer():

    # TODO: Add other Model Classes for Tables and auto populate with course info

    def __init__(self):
        if not database_file_path.is_file():
            # Create parent directory & database file if it does not exist
            database_file_path.parent.mkdir(parents=True, exist_ok=True)
            database_file_path.touch(exist_ok=True)
            # Initialize the new database file
            if database_file_path.is_file():
                with app.app_context():
                    # Creating Default Database Tables
                    db.create_all()


@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template('index.html')


@app.route('/landing', methods=['GET', 'POST'])
@login_required
def landing():
    user = request.args.get('user')
    id = request.args.get('id')
    return render_template('landing.html', user=user, id=id)


@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    flash('You have been successfully logged out.', 'success')
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()

    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        # Debug print to console
        if app.debug:
                if not user:
                    print(f"{form.username.data} not found in database.")
        if user:
            if bcrypt.check_password_hash(user.password, form.password.data):
                login_user(user)
                full_name = f"{user.students[0].first_name} {user.students[0].last_name}".title()
                return redirect(url_for('landing', user=full_name, id=user.students[0].student_id))
            
    return render_template('login.html', form=form)


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()

    if form.validate_on_submit():
        password_hash = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, password=password_hash)
        db.session.add(user)
        db.session.commit()
        student = Student(form.first_name.data, form.last_name.data, user.id)
        db.session.add(student)
        db.session.commit()
        flash('Registration successful! You may now login.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html', form=form)

def main():

    # Will check for database each app execution. If not found, creates a new blank database with User table
    DatabaseInitializer()

    # Using port tcp/8080 in testing.  Use port tcp/80 in prod (requires root). 
    # Note: This app does not use HTTPS - password is sent in cleartext across the wire
    app.run(host='0.0.0.0', port=8080, debug=True)

if __name__ == '__main__':
    main()
