import unittest
from unittest.mock import MagicMock, patch

from backend.services import UserService


class TestUserService(unittest.TestCase):

    def setUp(self):
        """Runs before each test"""
   
        self.mock_db_session = MagicMock()
        self.mock_keycloak_admin = MagicMock()

     
        self.user_service = UserService(self.mock_db_session, self.mock_keycloak_admin)


    def test_register_user_success(self):
        """Tests successful registration of user"""
      
        user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "a_very_secure_password",
            "keycloak_payload": {"username": "testuser", "email": "test@example.com"}
        }
 
        self.mock_keycloak_admin.create_user.return_value = "fake-user-id-123"

   
        self.user_service.register_user(user_data)

 
        self.mock_keycloak_admin.create_user.assert_called_once_with(user_data['keycloak_payload'])
  
        self.mock_keycloak_admin.set_user_password.assert_called_once_with("fake-user-id-123", user_data['password'], temporary=False)
   
        self.mock_db_session.add.assert_called_once()
        self.mock_db_session.commit.assert_called_once()


    def test_register_user_fails_with_short_password(self):
        """Tests registration fails with password that is too short"""
       
        user_data = {"password": "123"}

     
        with self.assertRaises(ValueError) as context:
            self.user_service.register_user(user_data)

        self.assertIn("at least 8 characters long", str(context.exception))

        self.mock_keycloak_admin.create_user.assert_not_called()
        self.mock_db_session.add.assert_not_called()

    @patch('backend.api.keycloak_openid') 
    def test_login_success(self, mock_keycloak_openid):
        """Tests successful login"""
        # Configure the mock to return a fake token
        expected_token = {"access_token": "a-fake-token"}
        mock_keycloak_openid.token.return_value = expected_token

        # Call the method on the service
        token = self.user_service.login("testuser", "correct_password")

        # Check the result and the interaction with the mock
        self.assertEqual(token, expected_token)
        mock_keycloak_openid.token.assert_called_with("testuser", "correct_password")


    @patch('backend.api.keycloak_openid')
    def test_login_failure(self, mock_keycloak_openid):
        """Tests failed login"""
        from keycloak.exceptions import KeycloakAuthenticationError
        # Configure the mock to raise an exception on login
        mock_keycloak_openid.token.side_effect = KeycloakAuthenticationError("Invalid credentials")

        # Check that the service correctly propagates the exception
        with self.assertRaises(KeycloakAuthenticationError):
            self.user_service.login("testuser", "wrong_password")

if __name__ == '__main__':
    unittest.main()