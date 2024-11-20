from datetime import datetime, timedelta, timezone
from flask import flash, Flask, redirect, render_template, request, session, url_for
from flask_bcrypt import Bcrypt
from flask_login import current_user, login_required, login_user, logout_user, LoginManager, UserMixin
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from itertools import chain
from json import load
from os import urandom
from pathlib import Path
from random import randint
from re import match, search
from redis import Redis
from sqlalchemy import asc, JSON
from sqlalchemy.orm import validates
from wtforms import PasswordField, StringField, SubmitField
from wtforms.validators import InputRequired, Length, ValidationError, DataRequired, Email
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.ext.mutable import MutableList
from sqlalchemy.types import JSON

def init_application():
    # paths to account for package directory structure (see README)
    parent_directory = Path(__file__).resolve().parent.parent
    database_path = parent_directory / 'database'
    database_file_path = Path(f"{database_path}/database.db")
    templates_path = 'templates'
    # Application
    app = Flask(__name__, template_folder=templates_path)
    app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{database_file_path}"
    app.config['SECRET_KEY'] = urandom(24)
    #app.config['SESSION_TYPE'] = 'filesystem'
    app.config['SESSION_TYPE'] = 'redis'
    app.config['SESSION_KEY_PREFIX'] = 'ocr_app_session:'
    app.config['SESSION_PERMANENT'] = True
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=60)
    #app.config['REDIS_URL'] = "redis://127.0.0.1:6379/1"
    redis_url = Redis.from_url('redis://127.0.0.1:6379/0')     
    app.config['SESSION_REDIS'] = redis_url    
    # Database
    db = SQLAlchemy(app)
    # Encryption for Password Storage
    bcrypt = Bcrypt(app)
    # Login Manager
    login_mgr = LoginManager(app)
    #login_mgr.init_app(app)    # replaced by including (app) in the constructor above
    login_mgr.login_view = "login"
    # Flask Session
    flask_session = Session(app)

    return database_file_path, database_path, app, db, bcrypt, login_mgr, flask_session

database_file_path, database_path, app, db, bcrypt, login_mgr, flask_session = init_application()

@login_mgr.user_loader
def load_user(id):
    #user_loaded = User.query.get(int(id))
    # Replaced deprecated User.query with db.session.get
    user_loaded = db.session.get(User, int(id))
    #print(user_loaded)
    return user_loaded

# Default Database Table : Users
class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    student = db.relationship('Student', back_populates='user', uselist=False)
    username = db.Column(db.String(64), nullable=False, unique=True)
    password = db.Column(db.String(80), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, onupdate=datetime.now(timezone.utc), nullable=True)     

    # Changing the default representation
    def __repr__(self):
        """ Changes the default representation 
        Args:
            None
        Returns:
            None
        """
        return f'{self.username}'

# Default Database Table : Students
class Student(db.Model):
    __tablename__ = 'students'
    # Establishing a relationship to the User class
    id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    user = db.relationship('User', back_populates='student')
    student_id = db.Column(db.Integer, unique=True, nullable=False)
    first_name = db.Column(db.String(30), nullable=False)
    last_name = db.Column(db.String(30), nullable=False)
    updated_at = db.Column(db.DateTime, onupdate=datetime.now(timezone.utc), nullable=True)
    student_email = db.Column(db.String(64), nullable=False)
    phone_number = db.Column(db.String(10), nullable=False)
    current_enrollments = db.Column(JSON, nullable=True)
    past_enrollments = db.Column(JSON, nullable=True)
    cart = db.Column(MutableList.as_mutable(JSON), default=[])
    registered_courses = db.Column(MutableList.as_mutable(JSON), default=[])
    
    def __init__(self, first_name, last_name, id, email, phone):
        self.id = id
        self.first_name = first_name.lower()
        self.last_name = last_name.lower()
        self.student_id = self.generate_student_id()
        self.student_email = email
        self.phone_number = phone

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
    
    def add_course_to_cart(self, class_selected):
        """Gives students ability to add a course to their cart
        Args:
            add_course_to_cart(Class):
        Returns:
            None
        """
        if not self.cart:
            self.cart = []
    
        if class_selected.class_id in self.cart:
            flash(f"Class {class_selected.class_id}:{class_selected.course_id} is already in the cart.", "info")
        else:
            self.cart.append(class_selected.class_id)
            # Mark the JSON column as modified so SQLAlchemy detects the change
            flag_modified(self, "cart")
            db.session.commit()
            flash(f"Class {class_selected.class_id}:{class_selected.course_id} added to cart!", "success")

        #print(f"Updated cart contents (Student ID: {self.student_id}): {self.cart}")
            
    def remove_course_from_cart(self, class_selected):
        """Removes a class from the cart
        Args:
            None
        Returns:
            None
        """
        if class_selected.class_id in self.cart:
            self.cart.remove(class_selected.class_id)
            flag_modified(self, "cart")
            db.session.commit()
            flash(f"Class {class_selected.class_id}:{class_selected.course_id} removed from cart.", "success")
        else:
            flash(f"Class {class_selected.class_id}:{class_selected.course_id} is not in the cart.", "info")
    
    def clear_cart(self):
        """Empties the cart or list of course
        Args:
            None
        Returns:
            None
        """
        self.cart = []
        flag_modified(self, "cart")
        db.session.commit()

    def register_cart_courses(self):
        if not self.cart:
            flash("Your cart is empty. No courses to register.", "warning")
            return

        for class_id in self.cart[:]:
            class_selected = Class.query.filter(Class.class_id == class_id).first()
            if class_id not in self.registered_courses:
                self.registered_courses.append(class_id)
                flash(f"Successfully registered for {class_selected.class_id}:{class_selected.course_id}!", "success")
            else:
                flash(f"Course {class_selected.class_id}:{class_selected.course_id} is already registered.", "info")
            
        self.cart.clear()
        flag_modified(self, "cart")
        flag_modified(self, "registered_courses")    
        db.session.commit()
        flash("All selected courses have been registered successfully.", "success")

    def view_registered_courses(self):
        if not self.registered_courses:
            print("No registered courses.")
        else:
            print("Registered Courses:")
            for class_id in self.registered_courses:
                print(f"{class_id}")
            

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

    @staticmethod
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


# Default Database Table : Semesters
class Semester(db.Model):
    __tablename__ = 'semesters'
    semester_name = db.Column(db.String(12), primary_key=True, nullable=False, unique=True)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)

    @staticmethod
    def init_database_semesters():
        json_file_path = 'initial_semester_dates.json'
        with open(json_file_path, 'r') as semester_data_file:
            semesters_data_data = load(semester_data_file)

        for semester_data in semesters_data_data:
            semester = Semester(
                semester_name = semester_data['semester_name'],
                start_date = datetime.strptime(semester_data['start_date'], "%m/%d/%Y"),
                end_date = datetime.strptime(semester_data['end_date'], "%m/%d/%Y")
            )
            # Add each new semester to the database
            db.session.add(semester)
        try:
            db.session.commit()
            if app.debug:
                print("Semesters have been successfully added to the database.")
        except Exception as e:
            if app.debug:
                print(f"Error committing changes to the database: {e}")
            db.session.rollback()


# New Account Form
class RegisterForm(FlaskForm):
    
    def validate_username(self, username_field):
        existing_user = User.query.filter_by(username=username_field.data).first()
        if existing_user:
                raise ValidationError(f"Existing account found for username: {existing_user.username}.")

    def validate_password_complexity(self, password_field):
        password = password_field.data
        if not search(r'[A-Z]', password):
            raise ValidationError('Password must contain at least one uppercase letter.')
        if not search(r'[a-z]', password):
            raise ValidationError('Password must contain at least one lowercase letter.')
        if not search(r'\d', password):
            raise ValidationError('Password must contain at least one digit.')
        if not search(r'[!@#$%^&*(),.?":{}|<>]', password):
            raise ValidationError('Password must contain at least one special character from this list: !@#$%^&*(),.?":{}|<>')
    
    def validate_phone_number(self, phone_number_field):
        phone_number = phone_number_field.data
        # Ensure the phone number is exactly 10 digits
        if not match(r'^\d{10}$', phone_number):
            raise ValidationError('Phone number must be exactly 10 digits long. (e.g. 2105551234)')
        
    username = StringField(
        validators=[
            DataRequired(message="Username field is required."),
            Email(message="Invalid username.  The username must be an email address."),
            Length(min=4, max=80, message="Username must be between 4 and 80 characters."),
            validate_username
        ],
        render_kw={"placeholder": "Email"}
    )
    password = PasswordField(
        validators=[
            DataRequired(message="Password field is required."),
            Length(min=12, max=24, message="Password must be between 12 and 24 characters long."),
            validate_password_complexity
        ],
        render_kw={"placeholder": "Password"}
    )
    first_name = StringField(validators=[InputRequired(), Length(min=2, max=63)],
                           render_kw={"placeholder": "First Name"})
    last_name = StringField(validators=[InputRequired(), Length(min=2, max=63)],
                           render_kw={"placeholder": "Last Name"})
    phone_number = StringField(
        validators=[
            DataRequired(message="Phone number field is required."),
            Length(min=10, max=10, message="Phone number must be exactly 10 digits long (e.g. 2105551234)"),
            validate_phone_number  # Custom phone number validation
        ],
        render_kw={"placeholder": "Phone Number"}
    )
    submit = SubmitField("Register")

class ChangePasswordForm(FlaskForm):

    updated_password = None

    def validate_password_complexity(self, password_field):
        updated_password = password_field.data
        if not search(r'[A-Z]', updated_password):
            raise ValidationError('Password must contain at least one uppercase letter.')
        if not search(r'[a-z]', updated_password):
            raise ValidationError('Password must contain at least one lowercase letter.')
        if not search(r'\d', updated_password):
            raise ValidationError('Password must contain at least one digit.')
        if not search(r'[!@#$%^&*(),.?":{}|<>]', updated_password):
            raise ValidationError('Password must contain at least one special character from this list: !@#$%^&*(),.?":{}|<>')
        # Save New Password for comparion
        self.updated_password = updated_password
    
    def validate_same_passwords(self, confirmation_field):
        print(self.updated_password, confirmation_field.data)
        if self.updated_password != confirmation_field.data:
            raise ValidationError('Passwords must match.')

    new_password = PasswordField(
        validators=[
            DataRequired(message="New Password field is required."),
            Length(min=12, max=24, message="Password must be between 12 and 24 characters long."),
            validate_password_complexity
        ],
        render_kw={"placeholder": "Password"}
    )
    confirmation_password = PasswordField(
        validators=[
            DataRequired(message="Confirmation Password field is required."),
            Length(min=12, max=24, message="Password must be between 12 and 24 characters long."),
            validate_same_passwords
        ],
        render_kw={"placeholder": "Password"}
    )
    submit = SubmitField("Change Password")


# User Account Form
class LoginForm(FlaskForm):
    username = StringField(validators=[InputRequired(), Length(min=4, max=80)],
                           render_kw={"placeholder": "Username"})
    password = PasswordField(validators=[InputRequired(), Length(min=12, max=24)],
                           render_kw={"placeholder": "Password"})
    submit = SubmitField("Login")

# Creating the initial database
def init_database(database_file_path, app, db, course):
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
                Semester.init_database_semesters()
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
    session.clear()
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
            else:
                flash('[!] Failed login attempt. Please try a different password', 'failure')
    return render_template('login.html', form=form)

@app.route('/passwordchange', methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        #print(current_user.password)
        password_hash = bcrypt.generate_password_hash(form.new_password.data).decode('utf-8')
        print(password_hash)
        # Setting new password
        current_user.password = password_hash
        db.session.commit()
        # Forcing Re-login
        logout_user()
        session.clear()
        flash('Your password has been changed! Please login with your new password.', 'success')
        return redirect(url_for('login'))
    return render_template('change_password.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        password_hash = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, password=password_hash)
        db.session.add(user)
        db.session.commit()
        student = Student(form.first_name.data, form.last_name.data, user.id, form.username.data, form.phone_number.data)
        db.session.add(student)
        db.session.commit()
        flash('Registration successful! You may now login.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/add_to_cart', methods=['POST'])
@login_required
def add_to_cart():
    class_id = int(request.form.get('class_id'))
    class_selected = Class.query.filter_by(class_id=class_id).first()

    if class_selected:
        student = current_user.student
        student.add_course_to_cart(class_selected)
    else:
        flash(f"Class {class_selected.class_id}:{class_selected.course_id} not found!", 'error')

    return redirect(url_for('view_courses'))

@app.route('/cart')
@login_required
def view_cart():
    student = current_user.student
    #print(f"Current cart from DB for {student.first_name} {student.last_name}: {student.cart}")
    cart_courses = Class.query.filter(Class.class_id.in_(student.cart)).all()
    #print(cart_courses)
    #print(f"Cart Courses Retrieved: {[course.course_id for course in cart_courses]}")
    return render_template('view_cart.html', cart_courses=cart_courses)

@app.route('/remove_from_cart', methods=['POST'])
@login_required
def remove_from_cart():
    class_id = int(request.form.get('class_id'))
    student = current_user.student
    class_selected = Class.query.filter(Class.class_id == class_id).first()

    if class_id in student.cart:
        student.cart.remove(class_id)
        db.session.commit()
        flash(f"Class {class_selected.class_id}:{class_selected.course_id} removed from cart.", "success")
    else:
        flash(f"Class {class_selected.class_id}:{class_selected.course_id} not found in cart.", "info")

    return redirect(url_for('view_cart'))

@app.route('/registercourse', methods=['POST'])
@login_required
def register_courses():
    current_user.student.register_cart_courses()
    return redirect(url_for('view_cart'))

@app.route('/drop_course', methods=['POST'])
@login_required
def drop_course():
    class_id = int(request.form.get('class_id'))
    student = current_user.student
    class_selected = Class.query.filter(Class.class_id == class_id).first()

    if class_id in student.registered_courses:
        student.registered_courses.remove(class_id)
        # Mark the JSON column as modified
        flag_modified(student, "registered_courses")
        db.session.commit()
        flash(f"Class {class_selected.class_id}:{class_selected.course_id} has been successfully dropped.", "success")
    else:
        flash(f"Class {class_selected.class_id}:{class_selected.course_id} is not in your registered courses.", "info")
    
    return redirect(url_for('registered_courses'))

@app.route('/registered')
@login_required
def registered_courses():
    student = current_user.student
    # Fetch course objects for all course IDs in registered_courses
    registered_courses = Class.query.filter(Class.class_id.in_(student.registered_courses)).all()
    return render_template('registered_courses.html', registered_courses=registered_courses)

def main():
    
    # Will check for database each app execution. If not found, creates a new blank database with User table
    init_database(database_file_path, app, db, Course)

    # Using port tcp/8080 in testing.  Use port tcp/80 in prod (may require root). 
    # Note: This app does not use HTTPS - password is sent in cleartext across the wire
    app.run(host='0.0.0.0', port=8080, debug=True)

if __name__ == '__main__':
    main()
