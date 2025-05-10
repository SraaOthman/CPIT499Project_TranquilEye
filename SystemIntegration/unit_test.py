import unittest
from app import app
import sqlite3

class TestTranquilEye(unittest.TestCase):

    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()
        conn = sqlite3.connect('tranquileye.db')
        conn.execute("DELETE FROM user WHERE email = 'testemail@gmail.com'")
        conn.execute("INSERT INTO user (email, name, password) VALUES (?, ?, ?)",
                    ('testemail@gmail.com', 'Test User', 'CorrectPass123'))
        conn.commit()
        conn.close()

  

    # Test#1: Signup with valid inputs
    def test_signup_valid_gmail(self):
        # Delete email if it exists
        conn = sqlite3.connect('tranquileye.db')
        conn.execute("DELETE FROM user WHERE email = 'testemail@gmail.com'")
        conn.commit()
        conn.close()

        response = self.client.post('/signup', data={
            'name': 'Test User',
            'email': 'testemail@gmail.com',
            'password': 'StrongPass123',
            'confirmPassword': 'StrongPass123'
        }, follow_redirects=True, content_type='application/x-www-form-urlencoded')
        self.assertIn("تم إنشاء الحساب بنجاح", response.data.decode('utf-8'))

    # Test#2: Signup with non-Gmail email
    def test_signup_non_gmail(self):
        response = self.client.post('/signup', data={
            'name': 'Test User',
            'email': 'testemail2@hotmail.com',
            'password': 'StrongPass123',
            'confirmPassword': 'StrongPass123'
        }, follow_redirects=True, content_type='application/x-www-form-urlencoded')
        self.assertIn("يجب استخدام بريد إلكتروني من Gmail فقط", response.data.decode('utf-8'))

    # Test#3: Signup with weak password
    def test_signup_weak_password(self):
        response = self.client.post('/signup', data={
            'name': 'Test User',
            'email': 'testemail3@gmail.com', 
            'password': 'weakpass',
            'confirmPassword': 'weakpass'
        }, follow_redirects=True, content_type='application/x-www-form-urlencoded')
        self.assertIn("كلمة المرور ضعيفة", response.data.decode('utf-8'))

    # Test#4: Login with correct inputs
    def test_login_correct_inputs(self):
        response = self.client.post('/login', data={
            'email': 'testemail@gmail.com',
            'password': 'CorrectPass123' 
        }, follow_redirects=True, content_type='application/x-www-form-urlencoded')
        self.assertIn("لوحة تحكم الوالدين", response.data.decode('utf-8'))


    # Test#5: Login with wrong email
    def test_login_wrong_email(self):
        response = self.client.post('/login', data={
            'email': 'wrongemail@gmail.com',
            'password': 'StrongPass123'
        }, follow_redirects=True, content_type='application/x-www-form-urlencoded')
        self.assertIn("لا يوجد حساب بهذا البريد الإلكتروني", response.data.decode('utf-8'))

    # Test#6: Login with wrong password
    def test_login_wrong_password(self):
        response = self.client.post('/login', data={
            'email': 'testemail@gmail.com',
            'password': 'WrongPass123'
        }, follow_redirects=True, content_type='application/x-www-form-urlencoded')
        self.assertIn("كلمة المرور غير صحيحة", response.data.decode('utf-8'))

if __name__ == '__main__':
    unittest.main()
