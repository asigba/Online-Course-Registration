import shutil, sys, unittest
from bs4 import BeautifulSoup
from src.app import app, Course, database_file_path, database_path, db, init_application, init_database, User

class TestUserRegistration(unittest.TestCase):

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
            #print(f"\nSuccessfully deleted the database: {database_path}")
    
    def get_csrf_token(self):
        """
        Retrieves the CSRF token for the /login redirect to work correctly
        """
        response = self.client.get('/register')
        soup = BeautifulSoup(response.data, 'html.parser')
        csrf_token = soup.find('input', {'name': 'csrf_token'})['value']
        return csrf_token
    
    def test_register_user(self):
        """
        Tests creation of a user
        """
        response = self.client.post('/register', data={
            'username': 'student',
            'password': 'studentpassword',
            'first_name': 'Hello',
            'last_name': 'World',
            #'csrf_token': self.get_csrf_token()
            'csrf_token': self.csrf_token
        }, follow_redirects=True)
        #print(self.csrf_token)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.request.path.endswith('/login'), "The user is not being redirected to /login")
        self.assertIn(b'Registration successful! You may now login.', response.data)
        
        # Verify the user in the database
        with app.app_context():
            user = User.query.filter_by(username='student').first()
            self.assertIsNotNone(user)

    def test_reregister_same_user(self):
        """
        Tests that the same user cannot be recreated
        """
        response = self.client.post('/register', data={
            'username': 'student',
            'password': 'studentpassword',
            'first_name': 'Hello',
            'last_name': 'World',
            'csrf_token': self.csrf_token
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Existing account found for username: student.', response.data)      

if __name__ == '__main__':
    unittest.main()
