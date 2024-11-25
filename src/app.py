from datetime import date, datetime, timedelta, timezone
from flask import flash, Flask, redirect, render_template, request, session, url_for
from flask_bcrypt import Bcrypt
from flask_login import current_user, login_required, login_user, logout_user, LoginManager, UserMixin
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from itertools import chain
from json import dumps, load, loads
from os import urandom
from pathlib import Path
from random import randint
from re import match, search
from redis import Redis
from sqlalchemy import asc, JSON
from sqlalchemy.orm import joinedload, validates
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.ext.mutable import MutableList
from sqlalchemy.types import JSON
from wtforms import PasswordField, StringField, SubmitField
from wtforms.validators import InputRequired, Length, ValidationError, DataRequired, Email
from uuid import uuid4

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

    def __init__(self, username, password):
        self.username = username
        self.password = User.hash_password(password)

    # Changing the default representation
    def __repr__(self):
        """ Changes the default representation 
        Args:
            None
        Returns:
            None
        """
        return f'{self.username}'
    
    @staticmethod
    def hash_password(password):
        return bcrypt.generate_password_hash(password).decode('utf-8')
    
    @staticmethod
    def init_database_users():
        json_file_path = 'initial_student_user_data.json'
        with open(json_file_path, 'r') as student_user_data_file:
            student_user_data = load(student_user_data_file)

        if not student_user_data:
            return
        
        for student_user in student_user_data:
            user = User(
                username=student_user['username'],
                password=student_user['password']
            )
            # Add each new course to the database
            if user is not None:
                db.session.add(user)
        try:
            db.session.commit()

        except Exception as e:
            if app.debug:
                print(f"Error committing changes to the database: {e}")
            db.session.rollback()

# Default Database Table : Students
class Student(db.Model):
    __tablename__ = 'students'
    # Establishing a relationship to the User class
    id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    user = db.relationship('User', back_populates='student')
    student_id = db.Column(db.Integer, unique=True, nullable=False)
    first_name = db.Column(db.String(30), nullable=False)
    last_name = db.Column(db.String(30), nullable=False)
    student_email = db.Column(db.String(64), nullable=False)
    phone_number = db.Column(db.String(10), nullable=False)
    #current_enrollments = db.Column(JSON, nullable=True)
    #past_enrollments = db.Column(JSON, nullable=True)
    cart = db.Column(MutableList.as_mutable(JSON), default=[])
    registered_classes = db.Column(MutableList.as_mutable(JSON), default=[])
    course_transactions = db.Column(MutableList.as_mutable(JSON), default=[])
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, onupdate=datetime.now(timezone.utc), nullable=True)
    
    
    # student = Student(form.first_name.data, form.last_name.data, user.id, form.username.data, form.phone_number.data)
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
    def init_database_students():
        json_file_path = 'initial_student_user_data.json'
        with open(json_file_path, 'r') as student_user_data_file:
            student_user_data = load(student_user_data_file)

        if not student_user_data:
            return
        
        for student_user in student_user_data:
            user = User.query.filter_by(username=student_user['username']).first()
            
            student = Student(
                first_name=student_user['first_name'],
                last_name=student_user['last_name'],
                id=user.id,
                email=student_user['username'],
                phone=student_user['phone_number']
            )

            # Add each new student to the database
            if student is not None:
                db.session.add(student)
            
            # Direct registration without the cart involved (not normal function - for dev init/testing only)
            student.registered_classes = student_user['registered_classes']
            student.course_transactions = student_user['course_transactions']
            flag_modified(student, "registered_classes")
            flag_modified(student, "course_transactions")

            # Allocate seats automatically
            for class_id in student.registered_classes:
                class_selected = Class.get_class(class_id)
                if class_selected is not None:
                    db.session.add(class_selected)
                class_selected.allocate_seat()
                # manual log transaction
                transaction = Transaction(student, class_selected, Transaction.REGISTER)
                student.add_transaction_to_log(transaction.to_log_string())

            # Adding to cart via the normal functions
            for class_id in student_user['cart']:
                class_selected = Class.get_class(class_id)
                if class_selected is not None:
                    db.session.add(class_selected)
                student.add_course_to_cart(class_selected)
        try:
            db.session.commit()
        except Exception as e:
            if app.debug:
                print(f"Error committing changes to the database: {e}")
            db.session.rollback()

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
    
        proceed_with_add_to_cart = True

        # Course of the class being added to verify two of the same course are not in the cart
        course = Course.get_course(class_selected.course_id)
        cart_courses = []
        for cart_class_id in self.cart:
            cart_class_obj = Class.get_class(cart_class_id)
            cart_courses.append(Course.get_course(cart_class_obj.course_id))
        registered_courses = []
        registered_classes = []
        for reg_class_id in self.registered_classes:
            reg_class_obj = Class.get_class(reg_class_id)
            registered_courses.append(Course.get_course(reg_class_obj.course_id))
            registered_classes.append(reg_class_obj)

        if class_selected.class_id in self.cart:
            proceed_with_add_to_cart = False
            try:
                flash(f"Class {class_selected} is already in the cart.", "info")
            except:
                pass
        elif course in cart_courses:
            proceed_with_add_to_cart = False
            try:
                flash(f"Course {course} is already in the cart.", "info")
            except:
                pass
        elif course in registered_courses:
            # Making sure re-enrollments are later than previous enrollments
            for registered_class in registered_classes:
                if class_selected.course_id == registered_class.course_id:
                    class_selected_semester = Semester.get_semester(class_selected.semester)
                    registered_class_semester = Semester.get_semester(registered_class.semester)
                    semester_comp = class_selected_semester.compare_semester_to(registered_class_semester)
                    registered_class_semester_status = registered_class.get_semester_status()
                    if semester_comp != Semester.LATER or registered_class_semester_status != Semester.ENDED:
                        proceed_with_add_to_cart = False
            if proceed_with_add_to_cart == False:
                try:
                    flash(f"Course {course} has already been registered for.", "info")
                except:
                    pass
                        
        if proceed_with_add_to_cart:
            self.cart.append(class_selected.class_id)
            # Mark the JSON column as modified so SQLAlchemy detects the change
            flag_modified(self, "cart")
            db.session.commit()
            try:
                flash(f"Class {class_selected} added to cart!", "success")
            except:
                pass
            
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
            flash(f"Class {class_selected} removed from cart.", "success")
        else:
            flash(f"Class {class_selected} is not in the cart.", "info")
    
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

        # Registered Credits by Semester
        total_credits = {}
        for class_id in self.registered_classes:
            the_class = Class.get_class(class_id)
            total_credits.setdefault(the_class.semester, 0)
            total_credits[the_class.semester] += the_class.credits_awarded

        # Cart Credits by Semester
        for class_id in self.cart[:]:
            class_selected = Class.get_class(class_id)
            total_credits.setdefault(class_selected.semester, 0)
            # Checking Total Credits by Semester
            if (total_credits[class_selected.semester] + class_selected.credits_awarded) <= 12:
                total_credits[class_selected.semester] += class_selected.credits_awarded
            else:
                flash(f"You cannot register for more than 12 credits in a semester.", "failure")
                return None

        # If credits are good, start registering
        for class_id in self.cart[:]:
            class_selected = Class.get_class(class_id)
            if class_selected.available_seats > 0:
                if class_id not in self.registered_classes:
                    self.registered_classes.append(class_id)
                    self.log_transaction(class_selected, Transaction.REGISTER)
                    flash(f"Successfully registered for {class_selected}!", "success")
                else:
                    flash(f"Course {class_selected} is already registered.", "info")
            else:
                flash(f"Course {class_selected} does not have any available seats.", "failure")
                
        self.cart.clear()
        flag_modified(self, "cart")
        flag_modified(self, "registered_classes")
        db.session.commit()
        class_selected.allocate_seat()
        flash("All available classes selected have been registered successfully.", "success")

    # This method id for dev init from files
    def add_transaction_to_log(self, transaction):
        if not self.course_transactions:
            self.course_transactions = []
        self.course_transactions.append(transaction)
        flag_modified(self, "course_transactions")
        db.session.commit()
        #self.print_all_transactions()

    # This method if for normal app activity
    def log_transaction(self, current_class, action):
        transaction = Transaction(self, current_class, action)
        self.add_transaction_to_log(transaction.to_log_string())

    
    def print_all_transactions(self):
        for transaction_dump in self.course_transactions:
            transaction = loads(transaction_dump)
            print(transaction['student'], transaction['transaction_id'], transaction['datetime'], transaction['course'], transaction['class_id'], transaction['semester'], transaction['action'])

    def remove_course_from_registered(self, class_selected):
        if class_selected.class_id in self.registered_classes:
            self.registered_classes.remove(class_selected.class_id)
            if class_selected.get_semester_status() == Semester.UPCOMING:
                self.log_transaction(class_selected, Transaction.DROP)
            elif class_selected.get_semester_status() == Semester.IN_SESSION:
                self.log_transaction(class_selected, Transaction.WITHDRAW)
            # Mark the JSON column as modified
            try:
                flag_modified(self, "registered_classes")
            except:
                pass
            db.session.commit()
            class_selected.free_seat()
            flash(f"Class {class_selected} has been successfully dropped.", "success")
        else:
            flash(f"Class {class_selected} is not in your registered courses.", "info")
    
# Default Database Table : Courses
class Course(db.Model):
    __tablename__ = 'courses'
    _class = db.relationship('Class', back_populates='course')
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

        if not courses_data:
            return
        
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
            if course is not None:
                db.session.add(course)
        try:
            db.session.commit()
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
                        if new_class is not None:
                            db.session.add(new_class)
        try:
            db.session.commit()
        except Exception as e:
            if app.debug:
                print(f"Error committing changes to the database: {e}")
            db.session.rollback()

    @staticmethod
    def get_course(course_id):
        # Deprecated
        #return Course.query.get_or_404(course_id)
        return db.session.get(Course, course_id)
    
# Default Database Table : Classes
class Class(db.Model):

    __tablename__ = 'classes'
    class_id = db.Column(db.Integer, primary_key=True, nullable=False)
    course = db.relationship('Course', back_populates='_class')
    course_id = db.Column(db.String(7), db.ForeignKey('courses.course_id'))
    course_name = db.Column(db.String(250), nullable=True)
    #current_enrollments = db.Column(JSON, nullable=True)
    location = db.Column(db.String(64), nullable=False)
    semester = db.Column(db.String(8), nullable=False)
    professor = db.Column(db.String(64), nullable=False)
    credits_awarded = db.Column(db.Integer, nullable=False)
    available_seats = db.Column(db.Integer, nullable=False)

    # Changing the default representation
    def __repr__(self):
        """ Changes the default representation 
        Args:
            None
        Returns:
            None
        """
        return f'"Class: {self.course_id}, ID: {self.class_id}"'
    
    @staticmethod
    def get_class(class_id):
        current_class = Class.query.filter_by(class_id=class_id).first()

        if current_class is not None:
            current_class = db.session.merge(current_class)

        return current_class

    def allocate_seat(self):
        if self.available_seats > 0:
            self.available_seats -= 1
            db.session.commit()

    def free_seat(self):
        if self.available_seats < self.course.max_seats:
            self.available_seats += 1
            db.session.commit()

    def get_semester_status(self):
        today = date.today()
        semester = Semester.get_semester(self.semester)
        if semester.start_date <= today <= semester.end_date:
            return Semester.IN_SESSION
        elif semester.start_date > today:
            return Semester.UPCOMING
        elif semester.end_date <= today:
            return Semester.ENDED
        else:
            return Semester.INVALID

# Default Database Table : Semesters
class Semester(db.Model):

    # Statuses
    INVALID = 0
    ENDED = 1
    IN_SESSION = 2
    UPCOMING = 3
    # Comparisons
    EARLIER = 4
    SAME = 5
    LATER = 6

    __tablename__ = 'semesters'
    semester_name = db.Column(db.String(12), primary_key=True, nullable=False, unique=True)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)

    @staticmethod
    def init_database_semesters():
        json_file_path = 'initial_semester_dates.json'
        with open(json_file_path, 'r') as semester_data_file:
            semesters_data_data = load(semester_data_file)

        if not semesters_data_data:
            return
        
        for semester_data in semesters_data_data:
            semester = Semester(
                semester_name = semester_data['semester_name'],
                start_date = datetime.strptime(semester_data['start_date'], "%m/%d/%Y"),
                end_date = datetime.strptime(semester_data['end_date'], "%m/%d/%Y")
            )
            # Add each new semester to the database
            if semester is not None:
                db.session.add(semester)
        try:
            db.session.commit()
        except Exception as e:
            if app.debug:
                print(f"Error committing changes to the database: {e}")
            db.session.rollback()

    @staticmethod
    def get_semester(semester_name):
        return Semester.query.filter_by(semester_name=semester_name).first()
    
    def compare_semester_to(self, other_semester):
        if self.start_date < other_semester.start_date:
            return Semester.EARLIER
        elif self.start_date == other_semester.start_date:
            return Semester.SAME
        elif self.start_date > other_semester.start_date:
            return Semester.LATER

class Transaction():

    INVALID = 0
    REGISTER = 1
    DROP = 2
    WITHDRAW = 3
    COMPLETE = 4

    transaction = {
            "student": None,
            "transaction_id": None,
            "datetime": None,       
            "course": None,
            "class_id": None,
            "semester": None,
            "action": None
    }
    
    def __init__(self, student, current_class, action):
        self.transaction['student'] = student.student_id
        self.transaction['transaction_id'] = str(uuid4())
        self.transaction['datetime'] = datetime.now(timezone.utc).isoformat()
        self.transaction['course'] = current_class.course_id
        self.transaction['class_id'] = current_class.class_id
        self.transaction['semester'] = current_class.semester
        self.transaction['action'] = Transaction.get_action(action)

    # JSON Serialization
    def __repr__(self):
        return dumps(self.transaction)
    
    @staticmethod
    def get_action(int):
        match int:
            case 1:
                return "register"
            case 2:
                return "drop"
            case 3:
                return "withdraw"
            case 4:
                return "complete"
    
    def to_log_string(self):
        return dumps(self.transaction)

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
        default='student01@student.umgc.edu',
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
    first_name = StringField(default='Hello', validators=[InputRequired(), Length(min=2, max=63)],
                           render_kw={"placeholder": "First Name"})
    last_name = StringField(default='World', validators=[InputRequired(), Length(min=2, max=63)],
                           render_kw={"placeholder": "Last Name"})
    phone_number = StringField(
        default='2105551234',
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
    username = StringField(default='student01@student.umgc.edu', validators=[InputRequired(), Length(min=4, max=80)],
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
                # Create Default User/Student Account
                User.init_database_users()
                Student.init_database_students()


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

    search_query = None
    search_results = []
    
    if 'reset' in request.args:
        # Redirect to the same route without query parameters
        return redirect(url_for('view_courses'))

    # Set Filter Values Selected
    selected_location = request.args.get('location', '')
    selected_semester = request.args.get('semester', '')
    selected_professor = request.args.get('professor', '')
    selected_catalog = request.args.get('catalog', '')
    hide_courses_registered_bool = request.args.get('hide_courses_registered', '')

    if request.method == 'GET':
        search_results = Course.query.order_by(asc(Course.course_id)).all()
    elif request.method == 'POST':
        # Getting search query results instead of all courses
        search_query = request.form.get('search')
        if search_query:
            search_results = Course.query.filter(
                (Course.catalog.ilike(f"%{search_query}%")) |
                (Course.course_number.ilike(f"%{search_query}%")) |
                (Course.course_id.ilike(f"%{search_query}%")) |
                (Course.semesters_offered.ilike(f"%{search_query}%")) |
                (Course.course_name.ilike(f"%{search_query}%")) |
                (Course.description.ilike(f"%{search_query}%")) |
                (Course.faculty.ilike(f"%{search_query}%"))
            ).all()

    # Start with All Courses
    all_courses = search_results[:]
    filtered_courses = all_courses[:]

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
        if hide_courses_registered_bool:
            student = current_user.student
            for class_id in student.registered_classes:
                registered_class = Class.get_class(class_id)
                # Remove any courses already registered for
                if registered_class.course_name == course.course_name:
                    try:
                        filtered_courses.remove(course)
                    except:
                        pass
            # Saving remaining courses
            all_courses = filtered_courses

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
        professors=professors,
        results=search_results,
        query=search_query
    )

@app.route('/course/<course_id>')
@login_required
def course_details(course_id):
    
    # Set Filter Values Selected
    selected_location = request.args.get('location', '')
    selected_semester = request.args.get('semester', '')
    selected_professor = request.args.get('professor', '')
    show_all_classes_bool = request.args.get('show_all_classes', '')

    # Course Selected
    course = Course.get_course(course_id)
    
    # Get All Classes of the Selected Course First
    all_classes = Class.query.filter_by(course_id=course_id).order_by(asc(Class.class_id))
    upcoming_classes = []
    display_classes = []
    for current_class in all_classes:
        semester_status = current_class.get_semester_status()
        if semester_status == Semester.UPCOMING:
            upcoming_classes.append(current_class)

    if show_all_classes_bool:
        display_classes = all_classes
    else:
        display_classes = upcoming_classes

    # Filter Classes By Selections
    if selected_location:
        display_classes = display_classes.filter_by(location=selected_location)
    if selected_semester:
        display_classes = display_classes.filter_by(semester=selected_semester)
    if selected_professor:
        display_classes = display_classes.filter_by(professor=selected_professor)

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
                           upcoming_classes=upcoming_classes,
                           display_classes=display_classes,
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
            flash(f"Username {form.username.data} not found in the database", 'failure')
        if user:
            # Password hashing for storing in the database
            password_match = bcrypt.check_password_hash(user.password, form.password.data)
            if password_match:
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
        password_hash = User.hash_password(form.new_password.data)
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
        user = User(username=form.username.data, password=form.password.data)
        if user is not None:
            db.session.add(user)
        db.session.commit()
        student = Student(form.first_name.data, form.last_name.data, user.id, form.username.data, form.phone_number.data)
        if student is not None:
            db.session.add(student)
        db.session.commit()
        flash('Registration successful! You may now login.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/add_to_cart', methods=['POST'])
@login_required
def add_to_cart():
    class_id = int(request.form.get('class_id'))
    class_selected = Class.get_class(class_id)
    course = Course.get_course(class_selected.course_id)
    student = current_user.student
    
    # Converting Class IDs into Class Objects
    registered_classes = []
    for class_id in student.registered_classes:
        current_class = Class.get_class(class_id)
        registered_classes.append(current_class)

    # Prereqs
    prereqs = course.prereqs
    prereq_met = False

    if prereqs:
        for prereq_id in prereqs:
            for registered_class in registered_classes:
                # If prereg matches a registered class
                if prereq_id == registered_class.course_id:
                    class_selected_semester = Semester.get_semester(class_selected.semester)
                    registered_class_semester = Semester.get_semester(registered_class.semester)
                    # Checking that prereq semester is later than registered class
                    semester_comp = class_selected_semester.compare_semester_to(registered_class_semester)
                    if semester_comp == Semester.LATER:
                        prereq_met = True

    # Return if preregs are no good
    if prereqs and not prereq_met:
        flash(f"[!] ERROR: Prerequisites have not been met!", 'error')
        return redirect(url_for('view_cart'))
                
    # Only allow classes that haven't started
    if class_selected.get_semester_status() == Semester.UPCOMING and (prereq_met == True or not prereqs):
        # Only allow classes with open seats available
        if class_selected.available_seats > 0:
            if class_selected:
                student.add_course_to_cart(class_selected)
            else:
                flash(f"{class_selected} not found!", 'error')
        else:
            flash(f"{class_selected} does not have any available seats.", "failure")
    else:
        flash(f"{class_selected} has already started or has invalid dates.", "failure")
    return redirect(url_for('view_cart'))

@app.route('/cart')
@login_required
def view_cart():
    student = current_user.student
    cart_courses = Class.query.filter(Class.class_id.in_(student.cart)).all()
    total_credits = sum(current_class.credits_awarded for current_class in cart_courses)
    return render_template('view_cart.html', cart_courses=cart_courses, total_credits=total_credits)

@app.route('/remove_from_cart', methods=['POST'])
@login_required
def remove_from_cart():
    class_id = int(request.form.get('class_id'))
    student = current_user.student
    class_selected = Class.get_class(class_id)

    if class_id in student.cart:
        student.cart.remove(class_id)
        db.session.commit()
        flash(f"Class {class_selected} removed from cart.", "success")
    else:
        flash(f"Class {class_selected} not found in cart.", "info")

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
    class_selected = Class.get_class(class_id)

    # Drop/Withdraw Result in the same action for now.  Future features may require separating the two.
    if class_selected.get_semester_status() == Semester.UPCOMING or class_selected.get_semester_status() == Semester.IN_SESSION:
        student.remove_course_from_registered(class_selected)
    else:
        flash(f"[!] ERROR: {student} cannot be unregistered from {class_selected}.", "failure")
    
    return redirect(url_for('registered_classes'))

@app.route('/registered')
@login_required
def registered_classes():
    student = current_user.student
    # Fetch course objects for all course IDs in registered_classes
    registered_classes = Class.query.filter(Class.class_id.in_(student.registered_classes)).all()
    return render_template('registered_classes.html', registered_classes=registered_classes, Semester=Semester)

@app.route('/log')
@login_required
def registration_log():
    student = current_user.student

    if 'reset' in request.args:
        # Redirect to the same route without query parameters
        return redirect(url_for('registration_log'))
    
    selected_action = request.args.get('action', '')

    transactions = []
    for transaction_record in student.course_transactions:
        transaction_dict = loads(transaction_record)

        # Converting ended registrations to completed (assumes a passing grade)
        if transaction_dict['action'] == Transaction.get_action(Transaction.REGISTER):
            current_class = Class.get_class(transaction_dict['class_id'])
            #class_semester = Semester.get_semester(current_class.semester)
            class_semester_status = current_class.get_semester_status()
            print(current_class.course_id, class_semester_status)
            if class_semester_status == Semester.ENDED:
                transaction_dict['action'] = Transaction.get_action(Transaction.COMPLETE)

        if selected_action and transaction_dict['action'] == selected_action:
            transactions.append(transaction_dict)
        elif not selected_action:
            transactions.append(transaction_dict)
    
    actions = [Transaction.get_action(Transaction.REGISTER), Transaction.get_action(Transaction.DROP), Transaction.get_action(Transaction.WITHDRAW), Transaction.get_action(Transaction.COMPLETE)]
    
    return render_template('registration_log.html', course_transactions=transactions, actions=actions, action=selected_action)

def main():
    
    # Will check for database each app execution. If not found, creates a new blank database with User table
    init_database(database_file_path, app, db, Course)

    # Using port tcp/8080 in testing.  Use port tcp/80 in prod (may require root). 
    # Note: This app does not use HTTPS - password is sent in cleartext across the wire
    app.run(host='0.0.0.0', port=8080, debug=True)

if __name__ == '__main__':
    main()
