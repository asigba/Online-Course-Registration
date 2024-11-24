# Online Course Registration 
![alt text](../images/banner.png)  
Our project will simplify the course registration process, allowing students to easily browse available courses, view detailed information, and register with just a few clicks. However, these features are accessible only after the student has successfully completed a secure login or registration process.  

# Installation Commands - commented-out commands may not be necessary
```
# Step 1: Python Reqs
sudo apt update -y
sudo apt install -y python3-pip python3-venv python3-dev redis-server
sudo service redis-server restart
#sudo rm /usr/bin/python3; sudo ln -s /usr/bin/python3.<VERSION> /usr/bin/python3
#sudo ln -s /usr/bin/python3 /usr/bin/python

# Step 2: Virutal Environment Setup
cd </mtn/c/Users/...>; python3 -m venv .venv495
source ./.venv495/bin/activate
python3 -m ensurepip --upgrade

# Step 3: 'cd' into Project Package
cd ./Online-Course-Registration

# Step 4 - Option 1:
pip install -r requirements.txt
python3 src/app.py

# Step 4 - Option 2:
pip install Flask==3.0.3 Flask-Bcrypt==1.0.1 Flask-Login==0.6.3 Flask-SQLAlchemy==3.1.1 Flask-WTF==1.2.2 WTForms==3.2.1 beautifulsoup4==4.12.3 email-validator==2.2.0 Flask-Session==0.8.0 redis==5.2.0
python3 src/app.py

# Step 4 - Option 3:
#pip install build
#python3 -m build
pip install cmsc495project*.whl
sudo cmsc495
```

# Package Directory Structure

    /cmsc495project
    │
    ├── .vscode
    │   └── launch.json         # enables sudo via VSCode
    |
    ├── /database
    │   └── database.db         # this file and parent directory will be created automatic if non-existent
    │
    ├── /docs
    │   └── README.md
    │
    |
    ├── /src
    │   ├── app.py              # the main application
    |   |
    │   ├── package.json
    |   |
    │   ├── package-lock.json
    |   |
    │   ├── tailwind.config.js      # tailwind configuration
    │   │
    │   ├── /templates          # HTML templates
    │   │   ├── change_password.html
    │   │   ├── course_details.html
    │   │   ├── index.html
    │   │   ├── landing.html
    │   │   ├── login.html
    |   |   ├── navbar_base.html    
    │   │   ├── register.html
    │   │   ├── registered_classes.html
    |   |   ├── registration_log.html    
    │   │   ├── view_cart.html
    │   │   └── view_courses.html
    │   │    
    │   ├── node_modules
    │   │   └── <many_files>
    │   │    
    │   └── /static             # Static assets (CSS, JS, images)
    │       │ 
    │       ├── dist
    │       │   └── css
    |       |        ├── output.css   
    |       |        ├── styles.css   
    |       |        └── table.css
    │       │
    │       ├── images
    │       |   ├── banner.png
    │       |   ├── Logo.png
    │       |   └── tinybanner.png
    |       |
    |       └── resource
    |           └── input.css
    │
    ├── /tests
    │   └── test_app.py         # 'python -m unittest discover tests'
    │  
    ├── initial_course_data.json
    |
    ├── initial_semester_dates.json
    |
    ├── initial_student_user_data.json
    |
    ├── requirements.txt
    │  
    └── pyproject.toml          # for 'python -m build' when creating the wheel

# Database Commands
```
sqlite3 ../database/database.db  
.schema  
.tables  
select * from users;  
select * from students;  
select * from courses;  
select * from classes;  
.exit  
```

# Database Tables

    CREATE TABLE users (
            id INTEGER NOT NULL,
            username VARCHAR(64) NOT NULL,
            password VARCHAR(80) NOT NULL,
            created_at DATETIME NOT NULL,
            updated_at DATETIME,
            PRIMARY KEY (id),
            UNIQUE (username)
    );
    CREATE TABLE courses (
            catalog VARCHAR(4) NOT NULL,
            course_number INTEGER NOT NULL,
            course_id VARCHAR(7) NOT NULL,
            semesters_offered JSON,
            course_name VARCHAR(250),
            description VARCHAR(250),
            max_seats INTEGER NOT NULL,
            locations_offered JSON,
            prereqs JSON,
            faculty JSON,
            credits_awarded INTEGER NOT NULL,
            required_technology VARCHAR(250),
            reporting_instructions VARCHAR(250),
            PRIMARY KEY (course_id),
            UNIQUE (course_id)
    );
    CREATE TABLE semesters (
            semester_name VARCHAR(12) NOT NULL,
            start_date DATE NOT NULL,
            end_date DATE NOT NULL,
            PRIMARY KEY (semester_name),
            UNIQUE (semester_name)
    );
    CREATE TABLE students (
            id INTEGER NOT NULL, 
	    student_id INTEGER NOT NULL, 
	    first_name VARCHAR(30) NOT NULL, 
	    last_name VARCHAR(30) NOT NULL, 
	    student_email VARCHAR(64) NOT NULL, 
	    phone_number VARCHAR(10) NOT NULL, 
	    cart JSON, 
	    registered_classes JSON, 
	    course_transactions JSON, 
	    created_at DATETIME NOT NULL, 
	    updated_at DATETIME, 
	    PRIMARY KEY (id), 
	    FOREIGN KEY(id) REFERENCES users (id), 
	    UNIQUE (student_id)
    );
    CREATE TABLE classes (
            class_id INTEGER NOT NULL, 
            course_id VARCHAR(7), 
            course_name VARCHAR(250), 
            location VARCHAR(64) NOT NULL, 
            semester VARCHAR(8) NOT NULL, 
            professor VARCHAR(64) NOT NULL, 
            credits_awarded INTEGER NOT NULL, 
            available_seats INTEGER NOT NULL, 
            PRIMARY KEY (class_id), 
            FOREIGN KEY(course_id) REFERENCES courses (course_id)
    );

# Tailwindcss command
        npx tailwindcss -i ./static/resource/input.css -o ./static/dist/css/output.css --watch
