from datetime import datetime, timezone
from flask import flash, Flask, redirect, render_template, request, url_for
from flask_bcrypt import Bcrypt
from flask_login import current_user, login_required, login_user, logout_user, LoginManager, UserMixin
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from itertools import chain
from json import load
from pathlib import Path
from random import randint
from sqlalchemy import asc, JSON
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
    student = db.relationship('Student', back_populates='user', uselist=False)

    # Changing the default representation
    def __repr__(self):
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
    cart = db.Column(JSON, default=[])
    registered_courses = db.Column(JSON, default=[])
    

    # Establishing a relationship to the User class
    user = db.relationship('User', back_populates='student')

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
    
    def add_course_to_cart(self, course):
        if course.course_id not in self.cart:
            self.cart.append(course.course_id)
            db.session.commit()
            print(f"Course {course.course_id} added to cart.")
        else:
            print(f"Course {course.course_id} is already in the cart.")

    def clear_cart(self):
        self.cart = []
        db.session.commit()

    def register_cart_courses(self):
        if not self.cart:
            print("Your cart is empty. No courses to register.")
        else:
            for course_id in self.cart:
                if course_id not in self.registered_courses:
                    self.registered_courses.append(course_id)
                    print(f"Successfully registered for {course_id}")
                else:
                    print(f"Already registered for {course_id}")
            self.clear_cart()
            db.session.commit()

    def view_registered_courses(self):
        if not self.registered_courses:
            print("No registered courses.")
        else:
            print("Registered Courses:")
            for course_id in self.registered_courses:
                print(f"{course_id}")
            

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
        super().__init__(**kwargs)
        # Primary Key is a combination of two other attributes
        if not self.course_id and self.catalog and self.course_number:
            self.course_id = f"{self.catalog}{self.course_number}"

    # This will alidate and update "course_id" if the catalog or course number ever changes
    @validates('catalog', 'course_number')
    def validate_and_generate_course_id(self, key, value):
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
                    #db.drop_all()
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

    # Set Filter Values Selected
    selected_location = request.args.get('location', '')
    selected_semester = request.args.get('semester', '')
    selected_professor = request.args.get('professor', '')
    selected_catalog = request.args.get('catalog', '')

    # Start with All Courses
    all_courses = Course.query.order_by(asc(Course.course_id))
    filtered_courses = all_courses.all()

    # Convert List Options to Individual Options in Drop Down Menu
    semesters = list(set(chain.from_iterable(course.semesters_offered for course in all_courses)))
    locations = list(set(chain.from_iterable(course.locations_offered for course in all_courses)))
    professors = list(set(chain.from_iterable(course.faculty for course in all_courses)))
    catalogs = Course.query.with_entities(Course.catalog).distinct().all()
    
    # Sort Options
    semesters.sort()
    locations.sort()
    professors.sort()
    catalogs.sort()

    # Filter Selections
    for course in all_courses:
        if selected_semester:
            # Remove any courses not filtered for
            if not selected_semester in course.semesters_offered:
                try:
                    filtered_courses.remove(course)
                except:
                    pass
            # Saving remaining courses
            all_courses = filtered_courses
        if selected_location:
            # Remove any courses not filtered for
            if not selected_location in course.locations_offered:
                try:
                    filtered_courses.remove(course)
                except:
                    pass
            all_courses = filtered_courses
        if selected_professor:
            # Remove any courses not filtered for
            if not selected_professor in course.faculty:
                try:
                    filtered_courses.remove(course)
                except:
                    pass
            all_courses = filtered_courses
        if selected_catalog:
            # Remove any courses not filtered for
            if selected_catalog != course.catalog:
                try:
                    filtered_courses.remove(course)
                except:
                    pass
            all_courses = filtered_courses

    # Render
    return render_template(
        'view_courses.html', 
        courses=all_courses, 
        semesters=semesters, 
        locations=locations, 
        catalogs=[cat[0] for cat in catalogs],
        professors=professors
    )

@app.route('/course/<course_id>')
@login_required
def course_details(course_id):
    
    # Set Filter Values Selected
    selected_location = request.args.get('location', '')
    selected_semester = request.args.get('semester', '')
    selected_professor = request.args.get('professor', '')

    # Course Selected
    course = Course.query.get_or_404(course_id)

    # Get All Classes of the Selected Course First
    all_classes = Class.query.filter_by(course_id=course_id).order_by(asc(Class.class_id))

    # Filter Classes By Selections
    if selected_location:
        all_classes = all_classes.filter_by(location=selected_location)
    if selected_semester:
        all_classes = all_classes.filter_by(semester=selected_semester)
    if selected_professor:
        all_classes = all_classes.filter_by(professor=selected_professor)

    # Drop Down Selection Options
    locations = Class.query.with_entities(Class.location).distinct().all()
    semesters = Class.query.with_entities(Class.semester).distinct().all()
    professors = Class.query.with_entities(Class.professor).distinct().all()

    # Sort Options
    semesters.sort()
    locations.sort()
    professors.sort()

    # Render
    return render_template('course_details.html',
                           course=course,
                           all_classes=all_classes,
                           locations=[loc[0] for loc in locations],
                           semesters=[sem[0] for sem in semesters],
                           professors=[prof[0] for prof in professors])

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
                full_name = f"{user.student.first_name} {user.student.last_name}".title()
                return redirect(url_for('landing', user=full_name, id=user.student.student_id))
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

@app.route('/add_to_cart', methods=['POST'])
@login_required
def add_to_cart():
    course_id = request.form.get('course_id')
    course = Course.query.filter_by(course_id=course_id).first()
    if course:
        current_user.student.add_course_to_cart(course)
    return redirect(url_for('view_courses'))

@app.route('/cart')
@login_required
def view_cart():
    student = current_user.student
    # Fetch course objects for all course IDs in the cart
    cart_courses = Course.query.filter(Course.course_id.in_(student.cart)).all()
    return render_template('view_cart.html', cart_courses=cart_courses)

@app.route('/registercourse', methods=['POST'])
@login_required
def register_courses():
    current_user.student.register_cart_courses()
    return redirect(url_for('registered_courses'))

@app.route('/registered')
@login_required
def registered_courses():
    student = current_user.student
    # Fetch course objects for all course IDs in registered_courses
    registered_courses = Course.query.filter(Course.course_id.in_(student.registered_courses)).all()
    return render_template('registered_courses.html', registered_courses=registered_courses)

def main():
    # Will check for database each app execution. If not found, creates a new blank database with User table
    DatabaseInitializer()
    # Using port tcp/8080 in testing.  Use port tcp/80 in prod (may require root). 
    # Note: This app does not use HTTPS - password is sent in cleartext across the wire
    app.run(host='0.0.0.0', port=8080, debug=True)

if __name__ == '__main__':
    main()
