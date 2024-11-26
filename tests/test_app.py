import shutil, sys, unittest
from bs4 import BeautifulSoup
from src.app import app, Course, database_file_path, database_path, db, init_application, init_database, User

class TestUserRegistration(unittest.TestCase):

    username = 'student99@student.umgc.edu'
    password = 'student99STUDENT()'
    phone_number = '4435551234'
    first_name = 'ITSAME'
    last_name = 'MARIO'
    csrf_token = None

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
    

    def test_1_register_new_user_account(self):
        """
        Test case 1 - Register a new user account
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
        self.assertTrue(response.request.path.endswith('/login'), "The user is not being redirected to /login")
        self.assertIn(b'Registration successful! You may now login.', response.data)
        
        # Verify the user in the database
        with app.app_context():
            user = User.query.filter_by(username=self.username).first()
            self.assertIsNotNone(user)

    def test_2_registration_with_existing_username(self):
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

    def test_3_login_valid_credentials(self):
        """
        Test Case 3 - Login using valid account credentials
        """
        response = self.client.post('/login', data={
            'username': self.username,
            'password': self.password,
            'csrf_token': self.csrf_token
        }, follow_redirects=True)
        #print(self.username, self.password, self.csrf_token)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Student ID:', response.data)  

    def test_4_logout(self):
        """
        Test Case 4 - Logout of a user session
        """
        # Login first to logout
        self.test_3_login_valid_credentials()
        response = self.client.post('/logout', data={
            'csrf_token': self.csrf_token
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'You have been successfully logged out', response.data)  

    def test_5_unauthenticated_access(self):
        """
        Test Case 5 - App prevents access to @login_required routes
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
            'course_id': 'ARTS101',
            # will need to change this test once classes are added to cart versus courses
            #'class_id': '36',
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

    def test_6_add_class_to_cart(self):
        """
        Test Case 6 - Add a class to the cart
        """
        # Login first to logout
        self.test_3_login_valid_credentials()
        response = self.client.post('/add_to_cart', data={
            'class_id': '7',
            'csrf_token': self.csrf_token
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'added to cart!', response.data)

    def test_7_view_cart(self):
        """
        Test Case 7 - View cart empty and with class(es)
        """
        # Login first to logout
        self.test_3_login_valid_credentials()
        # View Empty Cart
        response = self.client.get('/cart', data={
            'csrf_token': self.csrf_token
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.request.path.endswith('/cart'), "The user is not being redirected to /cart")
        self.assertIn(b'Your Cart', response.data)
        # Add a class
        response = self.client.post('/add_to_cart', data={
            'class_id': '7',
            'csrf_token': self.csrf_token
        }, follow_redirects=True)
        # View Cart
        response = self.client.get('/cart', data={
            'csrf_token': self.csrf_token
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.request.path.endswith('/cart'), "The user is not being redirected to /cart")
        self.assertIn(b'Your Cart', response.data)
        self.assertIn(b'Course ID', response.data)

if __name__ == '__main__':
    unittest.main()
