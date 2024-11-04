# Online Course Registration 
Our project will simplify the course registration process, allowing students to easily browse available courses, view detailed   
information, and register with just a few clicks. However, these features are accessible only after the student has successfully   
completed a secure login or registration process.  


# Installation Pasta

apt install python3.13 python3.13-venv python3.13-dev  
sudo rm /usr/bin/python3; sudo ln -s /usr/bin/python3.13 /usr/bin/python3        
cd; python3 -m venv .venv495     
source ~/.venv495/bin/activate    
python3 -m ensurepip --upgrade    
pip install cmsc495project*.whl     
sudo cmsc495    


# Package Directory Structure

/cmsc495project  
│  
├── /database  
│   └── database.db         # this file and parent directory will be created automatic if non-existent  
│  
├── /src  
│   ├── app.py              # the main application  
|   |  
│   ├── /templates          # HTML templates  
│   │   ├── index.html  
│   │   ├── landing.html  
│   │   ├── login.html  
│   │   └── register.html  
|   |  
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
├── /docs  
│   └── README.md  
│      
└── pyproject.toml          # for 'python -m build' when creating the wheel  


# Database Commands
sqlite3 ../database/database.db  
.tables  
select * from user;  
select * from student;  
.exit  


# Database Tables

+--------------------------+  
|          User            |  
+--------------------------+  
| id (PK)     | Integer    |  
| username    | String(30) |  
| password    | String(80) |  
| created_at  | DateTime   |  
| updated_at  | DateTime   |  
+--------------------------+  

+---------------------------+  
|          Student          |  
+---------------------------+  
| id (PK, FK)  | Integer    |  
| student_id   | Integer    |  
| first_name   | String(30) |  
| last_name    | String(30) |  
| updated_at   | DateTime   |  
+---------------------------+  
