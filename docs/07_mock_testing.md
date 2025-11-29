
# Exercise 6.1







# Exercise 6.2: Service Testing with Mocks

This document explains how the requirements for service testing were fulfilled by implementing a UserService and testing it in isolation using mocks.

## Goal

The main goal was to test the application's business logic (the "Service Layer") without relying on external systems like a real database or the Keycloak authentication server. This is achieved by creating "mock" (or fake) versions of these external systems during testing.

---

## Part 1: Implementing the UserService

To separate the business logic from the web layer (API routes), a UserService class was created. This class contains the core logic for user-related operations.

File:  ...backend/services.py

This class is initialized with its dependencies (the database session and the Keycloak client), which allows us to replace them with mocks during testing.

```python
# backend/services.py

class UserService:
    def __init__(self, db_session, keycloak_admin_client):
        self.db = db_session
        self.keycloak_admin = keycloak_admin_client
    
    def register_user(self, user_data):
        
```

The UserService fulfills the following requirements:

- User Registration: Implemented in the register_user method.
- Password Validation: A check if not password or len(password) < 8: is included in the register_user method.
- User Login/Rejection: This logic is handled by the /api/login route in backend/api.py, which calls the Keycloak client. The behavior is verified in the mock tests.
- User Role Assignment: The principle is demonstrated in the create_group_service function, where the group creator is automatically assigned the 'admin' role.

---

## Part 2: Creating the Mock Test Suite

A dedicated test suite was created to test the UserService in complete isolation.

File: .../test_backend/test_user_service_mock.py

This test suite follows the 5-step process required by the exercise for each scenario.

### Example: Testing Successful User Registration

The test test_register_user_success demonstrates the process perfectly:

1.  Set up mocks: In the setUp method, fake versions of the database and Keycloak client are created.
    ```python
    self.mock_db_session = MagicMock()
    self.mock_keycloak_admin = MagicMock()
    self.user_service = UserService(self.mock_db_session, self.mock_keycloak_admin)
    ```
2.  Configure mock behavior: We tell the fake Keycloak client what to return when a method is called.
    ```python
    self.mock_keycloak_admin.create_user.return_value = "fake-user-id-123"
    ```
3.  Execute the service method: We call the actual register_user method on our service instance.
    ```python
    self.user_service.register_user(user_data)
    ```
4.  Verify outcomes and interactions: We check if our service called the mock objects with the correct parameters. This proves our logic works as expected.
    ```python
    self.mock_keycloak_admin.create_user.assert_called_once_with(...)
    self.mock_db_session.add.assert_called_once()
    ```




    # Exercise 6.3






    # Exercise 6.4