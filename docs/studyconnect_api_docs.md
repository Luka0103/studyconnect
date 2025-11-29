# StudyConnect API Documentation

---

| Method | Endpoint | Auth Required | Description |
|--------|---------|---------------|------------|
| POST | /login | No | Authenticate user and get access & refresh tokens |
| POST | /refresh | No | Refresh access token using refresh token |
| POST | /users/register | No | Register a new user in Keycloak and local DB |
| GET | /users/<user_id> | Yes | Get details of a specific user |
| PUT | /users/<user_id> | Yes | Update details of a specific user (self only) |
| POST | /tasks | Yes | Create a new task for logged-in user |
| GET | /tasks | Yes | Get all tasks of logged-in user |
| GET | /tasks/user/<user_id> | Yes | Get tasks for a specific user |
| PUT | /tasks/<task_id> | Yes | Update a specific task |
| POST | /groups | Yes | Create a new group |
| GET | /groups | Yes | Get all available groups |
| GET | /groups/user/<user_id> | Yes | Get all groups of a specific user |
| POST | /groups/join | Yes | Join an existing group |
| GET | /groups/<group_id>/members | Yes | Get members of a group |
| POST | /groups/<group_id>/kick | Yes | Kick a user from a group (admin only) |
| POST | /groups/<group_id>/add-admin | Yes | Promote a user to admin role |
| POST | /groups/<group_id>/leave | Yes | Leave a group |


---

## Global Overview

**StudyConnect API** is a backend service built with Flask that interacts with PostgreSQL and Keycloak for authentication. It provides endpoints for managing users, tasks, and groups in a collaborative environment.

**Base URL:** `http://localhost:5000/api`

**Authentication:**
- Keycloak tokens are required for protected endpoints.
- Include `Authorization: Bearer <access_token>` in headers.

## Authentication Endpoints

### Login
**POST** `/login`

**Request:**
```json
{
  "username": "exampleUser",
  "password": "examplePass"
}
```

**Response (200):**
```json
{
  "access_token": "<token>",
  "refresh_token": "<refresh_token>"
}
```

**Response (401):**
```json
{
  "error": "Login failed",
  "details": "Invalid credentials"
}
```

### Refresh Token
**POST** `/refresh`

**Request:**
```json
{
  "refresh_token": "<refresh_token>"
}
```

**Response (200):**
```json
{
  "access_token": "<new_access_token>",
  "refresh_token": "<new_refresh_token>"
}
```

---

## User Endpoints

### Get User Info
**GET** `/users/<user_id>`

**Response (200):**
```json
{
  "id": "user-id",
  "name": "username",
  "email": "user@example.com",
  "birthday": "1990-01-01",
  "faculty": "Engineering"
}
```

### Register User
**POST** `/users/register`

**Request:**
```json
{
  "firstName": "John",
  "lastName": "Doe",
  "username": "johndoe",
  "email": "johndoe@example.com",
  "password": "password123",
  "birthday": "1990-01-01",
  "faculty": "Engineering"
}
```

**Response (201):**
```json
{
  "message": "User registered successfully",
  "id": "user-id",
  "username": "johndoe",
  "email": "johndoe@example.com",
  "firstName": "John",
  "lastName": "Doe",
  "birthday": "1990-01-01",
  "faculty": "Engineering"
}
```

### Update User Info
**PUT** `/users/<user_id>`

**Request:**
```json
{
  "username": "newusername",
  "email": "newemail@example.com",
  "birthday": "1991-01-01",
  "faculty": "Science"
}
```

**Response (200):**
```json
{
  "id": "user-id",
  "username": "newusername",
  "email": "newemail@example.com",
  "birthday": "1991-01-01",
  "faculty": "Science"
}
```

---

## Task Endpoints

### Get Tasks for Current User
**GET** `/tasks`

**Response (200):**
```json
[
  {
    "id": 1,
    "title": "Complete assignment",
    "deadline": "2025-12-01T12:00:00",
    "kind": "homework",
    "priority": "high",
    "status": "pending",
    "progress": 0,
    "group": {"id": 1, "name": "Math Group"},
    "assignee": "user-id"
  }
]
```

### Get Tasks for Specific User
**GET** `/tasks/user/<user_id>`

**Response:** Same as above.

### Create Task
**POST** `/tasks`

**Request:**
```json
{
  "title": "Complete project",
  "deadline": "2025-12-05",
  "kind": "project",
  "priority": "medium",
  "status": "pending",
  "group_id": 1
}
```

**Response (201):**
```json
{
  "message": "Task created",
  "task": {
    "id": 2,
    "title": "Complete project",
    "deadline": "2025-12-05T00:00:00",
    "kind": "project",
    "priority": "medium",
    "status": "pending",
    "progress": 0,
    "group": {"id": 1, "name": "Math Group"},
    "assignee": "user-id"
  }
}
```

### Update Task
**PUT** `/tasks/<task_id>`

**Request:**
```json
{
  "status": "completed",
  "progress": 100
}
```

**Response (200):**
```json
{
  "message": "Task updated",
  "task": {
    "id": 2,
    "title": "Complete project",
    "deadline": "2025-12-05T00:00:00",
    "kind": "project",
    "priority": "medium",
    "status": "completed",
    "progress": 100,
    "group": {"id": 1, "name": "Math Group"},
    "assignee": "user-id"
  }
}
```

---

## Group Endpoints

### Get Groups for Current User
**GET** `/groups/user/<user_id>`

**Response (200):**
```json
[
  {
    "id": 1,
    "name": "Math Group",
    "description": "Group for math students",
    "groupNumber": "101",
    "inviteLink": "abcd1234",
    "members": ["user-id1", "user-id2"],
    "memberCount": 2,
    "role": "admin"
  }
]
```

### Get All Groups
**GET** `/groups`

**Response:** Same as above, but includes all groups regardless of membership.

### Create Group
**POST** `/groups`

**Request:**
```json
{
  "name": "Physics Group",
  "description": "Group for physics projects",
  "groupNumber": "102"
}
```

**Response (201):**
```json
{
  "message": "Group created",
  "group": {
    "id": 3,
    "name": "Physics Group",
    "description": "Group for physics projects",
    "groupNumber": "102",
    "inviteLink": "efgh5678",
    "members": [],
    "memberCount": 0,
    "role": "admin"
  }
}
```

### Join Group
**POST** `/groups/join`

**Request:**
```json
{
  "group_id": 3
}
```

**Response (200):**
```json
{
  "message": "User user-id joined group Physics Group",
  "group": {
    "id": 3,
    "name": "Physics Group",
    "description": "Group for physics projects",
    "groupNumber": "102",
    "inviteLink": "efgh5678",
    "members": ["user-id"],
    "memberCount": 1,
    "role": "member"
  }
}
```

### Get Group Members
**GET** `/groups/<group_id>/members`

**Response (200):**
```json
{
  "members": [
    {"id": "user-id", "username": "johndoe", "email": "johndoe@example.com", "role": "admin"}
  ]
}
```

### Kick User from Group
**POST** `/groups/<group_id>/kick`

**Request:**
```json
{
  "user_id": "user-to-kick"
}
```

**Response (200):**
```json
{
  "message": "User removed"
}
```

### Promote User to Admin
**POST** `/groups/<group_id>/add-admin`

**Request:**
```json
{
  "user_id": "user-to-promote"
}
```

**Response (200):**
```json
{
  "message": "User promoted"
}
```

### Leave Group
**POST** `/groups/<group_id>/leave`

**Response (200):**
```json
{
  "message": "You have left the group"
}
```

---

**Note:** All endpoints that require authentication must include the Bearer token in the `Authorization` header.

---

