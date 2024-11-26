import shutil, sys, unittest
from bs4 import BeautifulSoup
from src.app import app, Course, database_file_path, database_path, db, init_application, init_database, User

class TestUserRegistration(unittest.TestCase):

    csrf_token = None
    new_password = 'STUDENT()student99'
    #invalid vars
    non_email_username = 'student99'
    wrong_password = 'student999STUDENT()'
    bad_phone_number_format = '443-555-1234'
    short_password = 'Aa1!Bb2@'
    missing_specials_password = 'student99STUDENT99'
    missing_decimals_password = 'student()STUDENT()'
    missing_uppers_password = 'student99student()'
    missing_lowers_password = 'STUDENT99STUDENT()'

    # 10 users
    username = 'student99@student.umgc.edu'
    password = 'student99STUDENT()'
    phone_number = '4435551234'
    first_name = 'ITSAME'
    last_name = 'MARIO'
    
    username2 = 'student88@student.umgc.edu'
    password2 = 'student88STUDENT**'
    phone_number2 = '2105551234'
    first_name2 = 'ITSA'
    last_name2 = 'LUIGI'

    username3 = 'student77@student.umgc.edu'
    password3 = 'student77STUDENT#$'
    phone_number3 = '3015551234'
    first_name3 = 'PEACH'
    last_name3 = 'TOADSTOOL'

    username4 = 'student66@student.umgc.edu'
    password4 = 'student66STUDENT@!'
    phone_number4 = '2025551234'
    first_name4 = 'TOAD'
    last_name4 = 'KINOPIO'

    username5 = 'student55@student.umgc.edu'
    password5 = 'student55STUDENT<>'
    phone_number5 = '7035551234'
    first_name5 = 'BOWSER'
    last_name5 = 'KOOPA'

    username6 = 'student44@student.umgc.edu'
    password6 = 'student44STUDENT{}'
    phone_number6 = '4105551234'
    first_name6 = 'DAISY'
    last_name6 = 'SARASALAND'

    username7 = 'student33@student.umgc.edu'
    password7 = 'student33STUDENT|:'
    phone_number7 = '7575551234'
    first_name7 = 'YOSHI'
    last_name7 = 'SAURUS'

    username8 = 'student22@student.umgc.edu'
    password8 = 'student22STUDENT%^'
    phone_number8 = '5125551234'
    first_name8 = 'DONKEY'
    last_name8 = 'KONG'

    username9 = 'student11@student.umgc.edu'
    password9 = 'student11STUDENT&*'
    phone_number9 = '8135551234'
    first_name9 = 'WARIO'
    last_name9 = 'WARE'

    username10 = 'student00@student.umgc.edu'
    password10 = 'student00STUDENT()'
    phone_number10 = '6265551234'
    first_name10 = 'WALUIGI'
    last_name10 = 'WALUIGI'

    # Runs before every test
    def setUp(self):
        """
        """
        self.client = app.test_client()
        self.csrf_token = self.get_csrf_token()
        if self.csrf_token:
            #print(f"\nSuccessfully got the CSRF Token: {self.csrf_token}")
            # basically "pass"...
            print("", end="")
        else:
            print(f"There was a problem finding the CSRF Token: {self.csrf_token}")
            sys.exit()

    # Runs after every test
    def tearDown(self):
        """
        """
        pass

    # Runs before only first test
    @classmethod
    def setUpClass(cls):
        """
        """
        # Setting up the application
        init_application()
        # Setting up the database
        init_database(database_file_path, app, db, Course)
        if database_file_path.exists():
            #print(f"Successfully initialized the database: {database_path}")
            # basically "pass"...
            print("", end="")
        else:
            print(f"There was a problem finding the database: {database_path}")
            sys.exit()

    # Runs after last test
    @classmethod
    def tearDownClass(cls):
        """
        """
        if database_path.exists() and database_path.is_dir():
            # Deleting the database after all test complete
            shutil.rmtree(database_path)
            print(f"\nSuccessfully deleted the database: {database_path}")
    
    def get_csrf_token(self):
        """
        Retrieves the CSRF token for the /login redirect to work correctly
        """
        response = self.client.get('/register')
        soup = BeautifulSoup(response.data, 'html.parser')
        csrf_token = soup.find('input', {'name': 'csrf_token'})['value']
        return csrf_token
    
    def login_with_password(self, username, password):
        self.csrf_token = self.get_csrf_token()
        response = self.client.post('/login', data={
            'username': username,
            'password': password,
            'csrf_token': self.csrf_token
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        if password != self.wrong_password:
            pattern = rb'Student ID:\s*\d{8}'
            self.assertRegex(response.data, pattern, "The response does not include a valid 8-digit Student ID.")
        return response

    def test_01_register_new_user_account(self):
        """
        Test case 1 - Register a new user account
        """
        def register_user(self, username, password, phone, first, last, valid=True):
            response = self.client.post('/register', data={
                'username': username,
                'password': password,
                'phone_number': phone,
                'first_name': first,
                'last_name': last,
                'csrf_token': self.csrf_token
            }, follow_redirects=True)
            self.assertEqual(response.status_code, 200)
            if valid:
                self.assertTrue(response.request.path.endswith('/login'), "The user is not being redirected to /login")
                self.assertIn(b'Registration successful! You may now login.', response.data)
                # Verify the user in the database
                with app.app_context():
                    user = User.query.filter_by(username=username).first()
                    self.assertIsNotNone(user)
            else:
                self.assertFalse(response.request.path.endswith('/login'), "The user is not being redirected to /login")
            return response

        # Attempt with non-email username
        response = register_user(self, self.non_email_username, self.password, self.phone_number, self.first_name, self.last_name, valid=False)
        self.assertIn(b'Invalid username.  The username must be an email address.', response.data)

        # Attempt with bad phone number format
        response = register_user(self, self.username, self.password, self.bad_phone_number_format, self.first_name, self.last_name, valid=False)
        self.assertIn(b'Phone number must be exactly 10 digits long', response.data)

        # Good Attempt #1
        register_user(self, self.username, self.password, self.phone_number, self.first_name, self.last_name)

        # Good Attempt #2
        register_user(self, self.username2, self.password2, self.phone_number2, self.first_name2, self.last_name2)

        # Good Attempt #3
        register_user(self, self.username3, self.password3, self.phone_number3, self.first_name3, self.last_name3)

        # Good Attempt #4
        register_user(self, self.username4, self.password4, self.phone_number4, self.first_name4, self.last_name4)

        # Good Attempt #5
        register_user(self, self.username5, self.password5, self.phone_number5, self.first_name5, self.last_name5)

        # Good Attempt #6
        register_user(self, self.username6, self.password6, self.phone_number6, self.first_name6, self.last_name6)

        # Good Attempt #7
        register_user(self, self.username7, self.password7, self.phone_number7, self.first_name7, self.last_name7)

        # Good Attempt #8
        register_user(self, self.username8, self.password8, self.phone_number8, self.first_name8, self.last_name8)

        # Good Attempt #9
        register_user(self, self.username9, self.password9, self.phone_number9, self.first_name9, self.last_name9)

        # Good Attempt #10
        register_user(self, self.username10, self.password10, self.phone_number10, self.first_name10, self.last_name10)

    def test_02_registration_with_existing_username(self):
        """
        Test Case 2 - Application prevents new user account registration if the username already exists
        """
        response = self.client.post('/register', data={
            'username': self.username,
            'password': self.password,
            'phone_number': self.phone_number,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'csrf_token': self.csrf_token
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Existing account found for username:', response.data)      

    def test_03_login_valid_credentials(self):
        """
        Test Case 3 - Login using valid account credentials
        """
        self.login_with_password(self.username, self.password)
        self.login_with_password(self.username2, self.password2)
        self.login_with_password(self.username3, self.password3)
        self.login_with_password(self.username4, self.password4)
        self.login_with_password(self.username5, self.password5)
        self.login_with_password(self.username6, self.password6)
        self.login_with_password(self.username7, self.password7)
        self.login_with_password(self.username8, self.password8)
        self.login_with_password(self.username9, self.password9)
        self.login_with_password(self.username10, self.password10)

    def test_04_login_invalid_credentials(self):
        """
        Test Case 4 - Login using valid account credentials
        """
        response = self.login_with_password(self.username, self.wrong_password)
        self.assertIn(b'Failed login attempt. Please try a different password', response.data)  
        
    def test_05_logout(self):
        """
        Test Case 5 - Logout of a user session
        """
        # Login first to logout
        self.login_with_password(self.username, self.password)
        response = self.client.post('/logout', data={
            'csrf_token': self.csrf_token
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'You have been successfully logged out', response.data)  

    def test_06_unauthenticated_access(self):
        """
        Test Case 6 - App prevents access to @login_required routes
        """
        # Landing
        response = self.client.get('/landing', data={
            'csrf_token': self.csrf_token
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Please log in to access this page', response.data)
        self.assertTrue(response.request.path.endswith('/login'), "The user is not being redirected to /login")
        # Courses
        response = self.client.get('/courses', data={
            'csrf_token': self.csrf_token
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Please log in to access this page', response.data)
        self.assertTrue(response.request.path.endswith('/login'), "The user is not being redirected to /login")
        # Classes
        response = self.client.get('/course/ARTS101', data={
            'csrf_token': self.csrf_token
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Please log in to access this page', response.data)
        self.assertTrue(response.request.path.endswith('/login'), "The user is not being redirected to /login")
        # Registered Courses
        response = self.client.get('/registered', data={
            'csrf_token': self.csrf_token
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Please log in to access this page', response.data)
        self.assertTrue(response.request.path.endswith('/login'), "The user is not being redirected to /login")
        # Cart
        response = self.client.get('/cart', data={
            'csrf_token': self.csrf_token
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Please log in to access this page', response.data)
        self.assertTrue(response.request.path.endswith('/login'), "The user is not being redirected to /login")
        # Add to Cart
        response = self.client.post('/add_to_cart', data={
            'class_id': '76',
            'csrf_token': self.csrf_token
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Please log in to access this page', response.data)
        self.assertTrue(response.request.path.endswith('/login'), "The user is not being redirected to /login")
        # Register Course
        response = self.client.post('/registercourse', data={
            'csrf_token': self.csrf_token
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Please log in to access this page', response.data)
        self.assertTrue(response.request.path.endswith('/login'), "The user is not being redirected to /login")
        # Remove from Cart
        response = self.client.post('/remove_from_cart', data={
            'csrf_token': self.csrf_token
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Please log in to access this page', response.data)
        self.assertTrue(response.request.path.endswith('/login'), "The user is not being redirected to /login")
        # Log
        response = self.client.get('/log', data={
            'csrf_token': self.csrf_token
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Please log in to access this page', response.data)
        self.assertTrue(response.request.path.endswith('/login'), "The user is not being redirected to /login")
        # Drop Courses
        response = self.client.post('/drop_course', data={
            'csrf_token': self.csrf_token
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Please log in to access this page', response.data)
        self.assertTrue(response.request.path.endswith('/login'), "The user is not being redirected to /login")
        # Change Password
        response = self.client.post('/passwordchange', data={
            'csrf_token': self.csrf_token
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Please log in to access this page', response.data)
        self.assertTrue(response.request.path.endswith('/login'), "The user is not being redirected to /login")
        # Logout
        response = self.client.post('/logout', data={
            'csrf_token': self.csrf_token
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Please log in to access this page', response.data)
        self.assertTrue(response.request.path.endswith('/login'), "The user is not being redirected to /login")

    def test_07_view_and_edit_cart(self):
        """
        Test Case 7 - View cart empty and with classes added and removed
        """
        def view_test_cart():
            response = self.client.get('/cart', data={
                'csrf_token': self.csrf_token
            }, follow_redirects=True)
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.request.path.endswith('/cart'), "The user is not being redirected to /cart")
            self.assertIn(b'Your Cart', response.data)
            return response
        
        # Login first to logout
        self.login_with_password(self.username, self.password)
        # View Empty Cart
        response = view_test_cart()
        # Add a class
        response = self.client.post('/add_to_cart', data={
            'class_id': '7',
            'csrf_token': self.csrf_token
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'added to cart!', response.data)
        # View Cart
        response = view_test_cart()
        self.assertIn(b'CMSC101', response.data)
        # Remove from Cart
        response = self.client.post('/remove_from_cart', data={
            'class_id': '7',
            'csrf_token': self.csrf_token
        }, follow_redirects=True)
        # View Cart
        response = view_test_cart()
        self.assertNotIn(b'CMSC101', response.data)

    def test_08_password_changes(self):
        """
        Test Case 8 - Attempt bad password changes, then change with a valid password and revert to original password
        """
        def invalid_password_check(invalid_password):
            self.login_with_password(self.username, self.password)
            response = self.client.post('/passwordchange', data={
                'new_password': invalid_password,
                'confirmation_password': invalid_password,
                'csrf_token': self.csrf_token
            }, follow_redirects=True)
            self.assertEqual(response.status_code, 200)
            #print(response.data.decode('utf-8'))
            self.assertNotIn(b'Your password has been changed!', response.data)

        # Short Password
        invalid_password_check(self.short_password)
        # Password without special characters
        invalid_password_check(self.missing_specials_password)
        # Password without decimal digits
        invalid_password_check(self.missing_decimals_password)
        # Password without uppercase letters
        invalid_password_check(self.missing_uppers_password)
        # Password without lowercase letters
        invalid_password_check(self.missing_lowers_password)
        # New Valid Password
        self.login_with_password(self.username, self.password)
        response = self.client.post('/passwordchange', data={
            'new_password': self.new_password,
            'confirmation_password': self.new_password,
            'csrf_token': self.csrf_token
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Your password has been changed!', response.data)
        # Original Password
        self.login_with_password(self.username, self.new_password)
        response = self.client.post('/passwordchange', data={
            'new_password': self.password,
            'confirmation_password': self.password,
            'csrf_token': self.csrf_token
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Your password has been changed!', response.data)

    def test_09_user_info_spoof(self):
        """
        Test 9 - ensure current_user prevents user spoofing
        """
        self.login_with_password(self.username, self.password)
        response = self.client.get('/landing', data={
            # Spoofed Info
            'user': 'ITSA LUIGI',
            'id': None,
            'csrf_token': self.csrf_token
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        # Actual user info
        self.assertIn(b'Itsame Mario', response.data)
        self.assertNotIn(b'Student ID: None', response.data)


    def test_10_render_all_templates(self):
        """
        Test 10 = Make sure all templates render and return status code 200
        """
        templates = [
            "/landing",
            "/courses",
            "/course/ARTS101",
            "/login",
            "/passwordchange",
            "/register",
            "/cart",
            "/registered",
            "/log",
            "/"
        ]

        self.login_with_password(self.username, self.password)
        for template in templates:

            response = self.client.get(template, data={
                'csrf_token': self.csrf_token
            }, follow_redirects=True)
            self.assertTrue(response.request.path.endswith(template), f"The user is not being redirected to {template}")
            self.assertEqual(response.status_code, 200)


if __name__ == '__main__':
    unittest.main()
