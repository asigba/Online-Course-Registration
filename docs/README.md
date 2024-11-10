# Online Course Registration 
![alt text](../images/banner.png)  
Our project will simplify the course registration process, allowing students to easily browse available courses, view detailed information, and register with just a few clicks. However, these features are accessible only after the student has successfully completed a secure login or registration process.  


# Installation Commands - commented-out commands may not be necessary
```
# Step 1: Python Reqs & Symlinks
sudo apt install python3-pip python3-venv python3-dev
sudo ln -s /usr/bin/python3 /usr/bin/python
#sudo rm /usr/bin/python3; sudo ln -s /usr/bin/python3.<VERSION> /usr/bin/python3

# Step 2: Virutal Environment Setup Outside of the Git Directory
cd ./Online-Course-Registration/../; python -m venv .venv495
source ./.venv495/bin/activate
python -m ensurepip --upgrade

# Step 3: 'cd' into Project Package
cd ./Online-Course-Registration

# Step 4 - Installation Option 1:
pip install -r requirements.txt

# Step 4 - Installation Option 2:
pip install Flask==3.0.3 Flask-Bcrypt==1.0.1 Flask-Login==0.6.3 Flask-SQLAlchemy==3.1.1 Flask-WTF==1.2.2 WTForms==3.2.1

# Step 4 - Installation Option 3:
# made with 'pip install build; python -m build'
pip install cmsc495project*.whl

# Step 5 - Execute one of the commands below
# Note: 'cmsc495' will only work if installed via the *.whl
# Note: root is only needed if the port is set below 1024 - right now we have it at 8080, so sudo isn't necessary [[ app.run(host='0.0.0.0', port=8080, debug=True) ]]
cmsc495 || python src/app.py
sudo -s "PATH=$PATH" cmsc495 || sudo -s "PATH=$PATH" python src/app.py
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

# Tailwindcss command
        npx tailwindcss -i ./static/resource/input.css -o ./static/dist/css/output.css --watch
