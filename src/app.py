from datetime import datetime, timezone
from flask import flash, Flask, redirect, render_template, request, url_for
from flask_bcrypt import Bcrypt
from flask_login import login_required, login_user, logout_user, LoginManager, UserMixin
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from json import load
from pathlib import Path
from random import choice, randint
from sqlalchemy import JSON
from sqlalchemy.orm import validates
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

# User Loading
@login_mgr.user_loader
def load_user(id):
    return User.query.get(int(id))


# Default Database Table : Users
class User(db.Model, UserMixin):   
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(30), nullable=False, unique=True)
    password = db.Column(db.String(80), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, onupdate=datetime.now(timezone.utc), nullable=True)     

    def __repr__(self):
        """ This function changes the default representation. 
        Args: 
            current object or class
        Returns:
            current object's username
        """
        return f'{self.username}'

# Default Database Table : Students
class Student(db.Model):   
    __tablename__ = 'students'        
    id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    student_id = db.Column(db.Integer, unique=True, nullable=False)
    first_name = db.Column(db.String(30), nullable=False)
    last_name = db.Column(db.String(30), nullable=False)
    updated_at = db.Column(db.DateTime, onupdate=datetime.now(timezone.utc), nullable=True)
    email = db.Column(db.String(64), nullable=True)
    phone_number = db.Column(db.String(12), nullable=True)
    current_enrollments = db.Column(JSON, nullable=True)
    past_enrollments = db.Column(JSON, nullable=True)

    # Establishing a relationship to the User class
    user = db.relationship('User', backref='student')

    def __init__(self, first_name, last_name, id):
        """ This a constructor for the Student class.
        Args: 
            first_name(str): text of student's first name
            last_name(str): text of student's last name
            id(int): randomize sets of integers        
        Returns:
            None        
        """
        self.id = id
        self.first_name = first_name.lower()
        self.last_name = last_name.lower()
        self.student_id = self.generate_student_id()

    def __repr__(self):
        """ This function changes the default representation. 
        Args: 
            current object or class
        Returns:
            current object's credentials like full name and ID
        """
        return f'<Student {self.first_name} {self.last_name}, User ID: {self.student_id}>'

# Default Database Table : Courses
class Course(db.Model):
    __tablename__ = 'courses'
    catalog = db.Column(db.String(4), nullable=False)
    course_number = db.Column(db.Integer, nullable=False)
    course_id = db.Column(db.String(7), primary_key=True, unique=True)
    semesters_offered = db.Column(JSON, nullable=True)
    course_name = db.Column(db.String(250), nullable=True)
    description = db.Column(db.String(250), nullable=True)
    max_seats = db.Column(db.Integer, nullable=False)
    locations_offered = db.Column(JSON, nullable=True)
    prereqs = db.Column(JSON, nullable=True)
    faculty = db.Column(JSON, nullable=True)
    credits_awarded = db.Column(db.Integer, nullable=False)
    required_technology = db.Column(db.String(250), nullable=True)
    reporting_instructions = db.Column(db.String(250), nullable=True)

    def __init__(self, **kwargs):
        """ This is a constructor for the Course class

        Args: 
            **kwargs takes multiple keyword argument
        Returns:
            None
        """
        super().__init__(**kwargs)
        # Primary Key is a combination of two other attributes
        if not self.course_id and self.catalog and self.course_number:
            self.course_id = f"{self.catalog}{self.course_number}"
    
    @validates('catalog', 'course_number')
    def validate_and_generate_course_id(self, key, value):
        """ This will validate and update "course id" if the catalog or course number ever changes.
        Args:
            key(string):
            value(int):            
        Returns:
            None
        """
        if key == 'catalog':
            if not isinstance(value, str) or len(value) != 4:
                raise ValueError("Catalog must be a 4-character string.")
            value = value.upper()
        elif key == 'course_number':
            if not (100 <= value <= 999):
                raise ValueError("Course number must be a 3-digit integer.")

        # Updates "course_id" based on the new catalog and course_number
        if self.catalog and self.course_number:
            self.course_id = f"{self.catalog}{self.course_number}"
        return value

    @staticmethod
    def init_database_courses():
        json_file_path = 'initial_course_data.json'
        with open(json_file_path, 'r') as course_data_file:
            courses_data = load(course_data_file)

        for course_data in courses_data:
            course = Course(
                catalog=course_data['catalog'],
                course_number=course_data['course_number'],
                description=course_data['description'],
                course_name=course_data['course_name'],
                max_seats=course_data['max_seats'],
                credits_awarded=course_data['credits_awarded'],
                semesters_offered=course_data['semesters_offered'],
                locations_offered=course_data['locations_offered'],
                prereqs=course_data['prereqs'],
                faculty=course_data['faculty'],
                required_technology=course_data['required_technology'],
                reporting_instructions=course_data['reporting_instructions']
            )
            # Add each new course to the database
            db.session.add(course)
        try:
            db.session.commit()
            if app.debug:
                print("Courses have been successfully added to the database.")
        except Exception as e:
            if app.debug:
                print(f"Error committing changes to the database: {e}")
            db.session.rollback()

    def create_classes():
        all_courses = Course.query.all()

        # This would change if new feature is added to create new courses - works off initial_course_data.json
        for course in all_courses:
            for location in course.locations_offered:
                for semester in course.semesters_offered:
                    for faculty in course.faculty:
                        new_class = Class(
                            course_id=course.course_id,
                            course_name=course.course_name, 
                            location = location,
                            semester=semester,
                            professor=faculty,
                            credits_awarded=course.credits_awarded,
                            available_seats=course.max_seats
                        )
                        # Add each new class to the database
                        db.session.add(new_class)
        try:
            db.session.commit()
            if app.debug:
                print("Classes have been successfully added to the database.")
        except Exception as e:
            if app.debug:
                print(f"Error committing changes to the database: {e}")
            db.session.rollback()

# Default Database Table : Classes
class Class(db.Model):
    __tablename__ = 'classes'
    class_id = db.Column(db.Integer, primary_key=True, nullable=False)
    course_id = db.Column(db.String(7), db.ForeignKey('courses.course_id'))
    course_name = db.Column(db.String(250), nullable=True)
    current_enrollments = db.Column(JSON, nullable=True)
    location = db.Column(db.String(64), nullable=False)
    semester = db.Column(db.String(8), nullable=False)
    professor = db.Column(db.String(64), nullable=False)
    credits_awarded = db.Column(db.Integer, nullable=False)
    available_seats = db.Column(db.Integer, nullable=False)

# New Account Form
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

# USer Account Form
class LoginForm(FlaskForm):
    username = StringField(validators=[InputRequired(), Length(min=4, max=20)],
                           render_kw={"placeholder": "Username"})
    password = PasswordField(validators=[InputRequired(), Length(min=4, max=20)],
                           render_kw={"placeholder": "Password"})
    submit = SubmitField("Login")

# Creating the initial database
class DatabaseInitializer():

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
                    # Populate Courses
                    Course.init_database_courses()
                    # Create Classes from Courses
                    Course.create_classes()

# ROUTES...

@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template('index.html')

@app.route('/landing', methods=['GET', 'POST'])
@login_required
def landing():
    user = request.args.get('user')
    id = request.args.get('id')
    return render_template('landing.html', user=user, id=id)

@app.route('/courses', methods=['GET', 'POST'])
@login_required
def view_courses():
    all_courses = Course.query.all()
    return render_template('view_courses.html', courses=all_courses)

@app.route('/course/<course_id>')
@login_required
def course_details(course_id):
    course = Course.query.get_or_404(course_id)
    all_classes = Class.query.all()
    return render_template('course_details.html', course=course, all_classes=all_classes)

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
        if not user:
            if app.debug:
                print(f"{form.username.data} not found in database.")
            flash('Username not found in the database', 'failure')
        if user:
            # Password hashing for storing in the database
            if bcrypt.check_password_hash(user.password, form.password.data):
                login_user(user)
                full_name = f"{user.student[0].first_name} {user.student[0].last_name}".title()
                return redirect(url_for('landing', user=full_name, id=user.student[0].student_id))
    return render_template('login.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        password_hash = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, password=password_hash)
        db.session.add(user)
        db.session.commit()
        new_student = Student(form.first_name.data, form.last_name.data, user.id)
        db.session.add(new_student)
        db.session.commit()
        flash('Registration successful! You may now login.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

def main():
    # Will check for database each app execution. If not found, creates a new blank database with User table
    DatabaseInitializer()
    # Using port tcp/8080 in testing.  Use port tcp/80 in prod (may require root). 
    # Note: This app does not use HTTPS - password is sent in cleartext across the wire
    app.run(host='0.0.0.0', port=8080, debug=True)

if __name__ == '__main__':
    main()
