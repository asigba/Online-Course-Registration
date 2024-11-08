# Online Course Registration 
![alt text](../images/banner.png)  
Our project will simplify the course registration process, allowing students to easily browse available courses, view detailed information, and register with just a few clicks. However, these features are accessible only after the student has successfully completed a secure login or registration process.  


# Installation Pasta
```
apt install python3.13 python3.13-venv python3.13-dev  
sudo rm /usr/bin/python3; sudo ln -s /usr/bin/python3.13 /usr/bin/python3        
cd; python3 -m venv .venv495     
source ~/.venv495/bin/activate    
python3 -m ensurepip --upgrade    
pip install cmsc495project*.whl     
sudo cmsc495    
```

# Package Directory Structure

    /cmsc495project
    │
    ├── /database
    │   └── database.db         # this file and parent directory will be created automatic if non-existent
    │
    ├── /docs
    │   └── README.md
    │
    ├── /src
    │   ├── app.py              # the main application
    │   │
    │   ├── /templates          # HTML templates
    │   │   ├── course_details.html
    │   │   ├── index.html
    │   │   ├── landing.html
    │   │   ├── login.html
    │   │   ├── register.html
    │   │   └── view_courses.html
    │   │
    │   └── /static             # Static assets (CSS, JS, images)
    │       ├── css
    │       │   └── <style.css>
    │       ├── js
    │       │   └── <script.js>
    │       └── images
    │           └── <logo.png>
    │
    ├── /tests
    │   └── <test.py>
    │  
    ├── initial_course_data.json
    │  
    └── pyproject.toml          # for 'python -m build' when creating the wheel

![alt text](../images/directory_stucture.png)

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
            username VARCHAR(30) NOT NULL,
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
    CREATE TABLE students (
            id INTEGER NOT NULL,
            student_id INTEGER NOT NULL,
            first_name VARCHAR(30) NOT NULL,
            last_name VARCHAR(30) NOT NULL,
            updated_at DATETIME,
            email VARCHAR(64),
            phone_number VARCHAR(12),
            current_enrollments JSON,
            past_enrollments JSON,
            PRIMARY KEY (id),
            FOREIGN KEY(id) REFERENCES users (id),
            UNIQUE (student_id)
    );
    CREATE TABLE classes (
            class_id INTEGER NOT NULL,
            course_id VARCHAR(7),
            course_name VARCHAR(250),
            current_enrollments JSON,
            location VARCHAR(64) NOT NULL,
            semester VARCHAR(8) NOT NULL,
            professor VARCHAR(64) NOT NULL,
            credits_awarded INTEGER NOT NULL,
            available_seats INTEGER NOT NULL,
            PRIMARY KEY (class_id),
            FOREIGN KEY(course_id) REFERENCES courses (course_id)
    );
