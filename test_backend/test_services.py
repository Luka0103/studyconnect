import os
import sys
import importlib.util
from types import SimpleNamespace, ModuleType
from unittest.mock import Mock
from datetime import date, datetime
import pytest

# Mock classes for testing
class MockQuery:
    """Helper class to mock SQLAlchemy query interface"""
    def filter(self, *args):
        return self
    def first(self):
        return None
    def all(self):
        return []
    def get(self, id):
        return None

class FakeUser:
    query = None
    def __init__(self, id=None, username=None, email=None):
        self.id = id
        self.username = username
        self.email = email
        self.groups = []

def make_fake_db():
    session = SimpleNamespace(add=Mock(), commit=Mock())
    return SimpleNamespace(session=session)

# Install a fake 'models' module into sys.modules so services can import it
fake_models = ModuleType("models")
fake_models.db = make_fake_db()
fake_models.User = FakeUser
fake_models.Group = SimpleNamespace()
fake_models.Task = SimpleNamespace()
sys.modules["models"] = fake_models

# load the services module from backend/services.py reliably
services_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend", "services.py"))
spec = importlib.util.spec_from_file_location("backend_services", services_path)
services = importlib.util.module_from_spec(spec)
spec.loader.exec_module(services)

class FakeTask:
    query = None
    # Class-level attributes für SQLAlchemy-Style Vergleiche
    title = object()
    deadline = object()
    user_id = object()
    group_id = object()
    status = object()
    progress = object()
    priority = object()
    assignee = object()

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


def test_get_or_create_user_from_keycloak_returns_existing_user():
    existing = FakeUser(id="u1", username="alice", email="alice@example.com")
    FakeUser.query = SimpleNamespace(get=lambda uid: existing)
    services.User = FakeUser
    services.db = make_fake_db()

    result = services.get_or_create_user_from_keycloak({
        "sub": "u1",
        "preferred_username": "alice",
        "email": "alice@example.com"
    })

    assert result is existing
    assert services.db.session.add.call_count == 0
    assert services.db.session.commit.call_count == 0


def test_get_or_create_user_from_keycloak_creates_and_commits_new_user():
    FakeUser.query = SimpleNamespace(get=lambda uid: None)
    services.User = FakeUser
    services.db = make_fake_db()

    kc_info = {"sub": "u2", "preferred_username": "bob", "email": "bob@example.com"}

    result = services.get_or_create_user_from_keycloak(kc_info)

    assert isinstance(result, FakeUser)
    assert result.id == "u2"
    assert result.username == "bob"
    assert result.email == "bob@example.com"
    services.db.session.add.assert_called_once_with(result)
    services.db.session.commit.assert_called_once()


def test_get_or_create_user_from_keycloak_raises_on_missing_sub():
    services.User = FakeUser
    services.db = make_fake_db()

    with pytest.raises(Exception) as excinfo:
        services.get_or_create_user_from_keycloak({"email": "noid@example.com"})
    assert "Missing Keycloak user ID" in str(excinfo.value)


# -----------------------------
# Tests for get_user_service
# -----------------------------
def test_get_user_service_returns_user_when_exists():
    existing = FakeUser(id="u10", username="carol", email="carol@example.com")
    FakeUser.query = SimpleNamespace(get=lambda uid: existing if uid == "u10" else None)
    services.User = FakeUser

    result = services.get_user_service("u10")

    assert result is existing

def test_get_user_service_raises_when_not_exists():
    FakeUser.query = SimpleNamespace(get=lambda uid: None)
    services.User = FakeUser

    with pytest.raises(Exception) as excinfo:
        services.get_user_service("missing")
    assert "does not exist" in str(excinfo.value)


# -----------------------------
# Tests for create_task_service (fixed: provide class-level attributes used in comparisons)
# -----------------------------
def test_create_task_service_returns_existing_task():
    data = {
        "title": "Homework",
        "deadline": "2025-10-30",
        "kind": "homework",
        "priority": "high",
        "user_id": "u1",
        "group_id": 1,
    }

    existing_task = FakeTask(
        title="Homework",
        deadline=date.fromisoformat("2025-10-30"),
        user_id="u1",
        group_id=1
    )

    # filter(...).first() should return existing_task
    FakeTask.query = SimpleNamespace(filter=lambda *a, **k: SimpleNamespace(first=lambda: existing_task))
    services.Task = FakeTask
    services.db = make_fake_db()

    result = services.create_task_service(data)
    assert result is existing_task
    assert services.db.session.add.call_count == 0
    assert services.db.session.commit.call_count == 0


def test_create_task_service_creates_and_commits_new_task():
    data = {
        "title": "Project",
        "deadline": "2025-11-01",
        "kind": "project",
        "priority": "medium",
        "user_id": "u2",
        "group_id": 2,
        "assignee": "u3",
        "notes": "Do research",
        "progress": 20
    }

    # filter(...).first() returns None (no duplicate)
    FakeTask.query = SimpleNamespace(filter=lambda *a, **k: SimpleNamespace(first=lambda: None))
    services.Task = FakeTask
    services.db = make_fake_db()

    result = services.create_task_service(data)

    assert isinstance(result, FakeTask)
    assert result.title == "Project"
    assert result.deadline == date.fromisoformat("2025-11-01")
    assert result.kind == "project"
    assert result.priority == "medium"
    assert result.user_id == "u2"
    assert result.group_id == 2
    assert result.assignee == "u3"
    assert result.notes == "Do research"
    assert result.progress == 20

    services.db.session.add.assert_called_once_with(result)
    services.db.session.commit.assert_called_once()


# -----------------------------
# Tests for update_task_service
# -----------------------------
def test_update_task_service_updates_fields_and_deadline():
    # prepare fake task class and existing instance
    class FakeTask:
        query = None
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    existing = FakeTask(
        id="t1",
        title="Old Title",
        deadline=date.fromisoformat("2025-10-01"),
        kind="homework",
        priority="low",
        status="todo",
        user_id="u1",
        group_id=1,
        assignee=None,
        notes="old",
        progress=0
    )

    FakeTask.query = SimpleNamespace(get=lambda tid: existing if tid == "t1" else None)
    services.Task = FakeTask
    services.db = make_fake_db()

    update_data = {
        "title": "New Title",
        "priority": "high",
        "status": "in_progress",
        "deadline": "2025-12-15",
        "progress": 75,
        "notes": "updated notes"
    }

    result = services.update_task_service("t1", update_data)

    assert result is existing
    assert result.title == "New Title"
    assert result.priority == "high"
    assert result.status == "in_progress"
    assert result.deadline == date.fromisoformat("2025-12-15")
    assert result.progress == 75
    assert result.notes == "updated notes"
    services.db.session.commit.assert_called_once()


def test_update_task_service_raises_when_task_not_found():
    class FakeTask:
        query = None

    FakeTask.query = SimpleNamespace(get=lambda tid: None)
    services.Task = FakeTask
    services.db = make_fake_db()

    with pytest.raises(Exception) as excinfo:
        services.update_task_service("missing-id", {"title": "x"})
    assert "does not exist" in str(excinfo.value)


# -----------------------------
# Tests for get_tasks_for_user
# -----------------------------
def test_get_tasks_for_user_returns_tasks_for_user_and_group():
    # helper types to emulate SQLAlchemy column expression behavior
    class DummyExpr:
        def __or__(self, other):
            return self
    class DummyColumn:
        def __eq__(self, other):
            return DummyExpr()
        def in_(self, seq):
            return DummyExpr()

    # prepare user with one group
    group = SimpleNamespace(id=2)
    user = FakeUser(id="u5", username="eve", email="eve@example.com")
    user.groups = [group]
    FakeUser.query = SimpleNamespace(get=lambda uid: user if uid == "u5" else None)
    services.User = FakeUser

    # fake Task class and two tasks: one owned by user, one belonging to group
    class FakeTask:
        # provide dummy columns so expressions like Task.user_id and Task.group_id.in_(...) work
        user_id = DummyColumn()
        group_id = DummyColumn()
        query = None
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    task_user = FakeTask(id="t1", user_id="u5", group_id=3)
    task_group = FakeTask(id="t2", user_id="other", group_id=2)

    # Task.query.filter(...).all() returns both tasks
    FakeTask.query = SimpleNamespace(filter=lambda *a, **k: SimpleNamespace(all=lambda: [task_user, task_group]))
    services.Task = FakeTask

    result = services.get_tasks_for_user("u5")
    assert result == [task_user, task_group]

def test_get_tasks_for_user_returns_empty_list_when_user_missing():
    FakeUser.query = SimpleNamespace(get=lambda uid: None)
    services.User = FakeUser

    result = services.get_tasks_for_user("nope")
    assert result == []

# -----------------------------
# Tests for get_all_tasks
# -----------------------------
def test_get_all_tasks_returns_all_tasks():
    class FakeTask:
        query = None
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    t1 = FakeTask(id="a")
    t2 = FakeTask(id="b")
    FakeTask.query = SimpleNamespace(all=lambda: [t1, t2])
    services.Task = FakeTask

    result = services.get_all_tasks()
    assert result == [t1, t2]

def test_get_all_tasks_returns_empty_list_when_none():
    class FakeTask:
        query = None
    FakeTask.query = SimpleNamespace(all=lambda: [])
    services.Task = FakeTask

    result = services.get_all_tasks()
    assert result == []

# -----------------------------
# Tests for create_group_service
# -----------------------------
def test_create_group_service_returns_existing_group():
    # helper type to emulate SQLAlchemy column expression behavior
    class DummyExpr:
        def __or__(self, other):
            return self
    class DummyColumn:
        def __eq__(self, other):
            return DummyExpr()

    # fake Group class with necessary column attributes
    class FakeGroup:
        group_number = DummyColumn()
        invite_link = DummyColumn()
        query = None
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    existing_group = FakeGroup(
        name="Study Group A",
        description="Test group",
        group_number="G123",
        invite_link="link123"
    )

    # filter(...).first() returns existing group
    FakeGroup.query = SimpleNamespace(filter=lambda *a, **k: SimpleNamespace(first=lambda: existing_group))
    services.Group = FakeGroup
    services.db = make_fake_db()

    data = {
        "name": "Study Group A",
        "description": "Test group",
        "groupNumber": "G123",
        "inviteLink": "link123"
    }

    result = services.create_group_service(data)
    assert result is existing_group
    assert services.db.session.add.call_count == 0
    assert services.db.session.commit.call_count == 0


def test_create_group_service_creates_and_commits_new_group():
    # helper type for SQLAlchemy expressions
    class DummyExpr:
        def __or__(self, other):
            return self
    class DummyColumn:
        def __eq__(self, other):
            return DummyExpr()

    class FakeGroup:
        group_number = DummyColumn()
        invite_link = DummyColumn()
        query = None
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    # filter(...).first() returns None (no duplicate)
    FakeGroup.query = SimpleNamespace(filter=lambda *a, **k: SimpleNamespace(first=lambda: None))
    services.Group = FakeGroup
    services.db = make_fake_db()

    data = {
        "name": "New Study Group",
        "description": "A fresh group",
        "groupNumber": "G999",
        "inviteLink": "newlink999"
    }

    result = services.create_group_service(data)

    assert isinstance(result, FakeGroup)
    assert result.name == "New Study Group"
    assert result.description == "A fresh group"
    assert result.group_number == "G999"
    assert result.invite_link == "newlink999"

    services.db.session.add.assert_called_once_with(result)
    services.db.session.commit.assert_called_once()


# -----------------------------
# Tests for join_group_service
# -----------------------------
def test_join_group_service_adds_user_to_group():
    # Setup fake user and group
    user = FakeUser(id="u7", username="frank", email="frank@example.com")
    user.groups = []
    
    class FakeGroup:
        query = None
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    group = FakeGroup(id=3, name="Test Group")

    # Setup queries
    FakeUser.query = SimpleNamespace(get=lambda uid: user if uid == "u7" else None)
    FakeGroup.query = SimpleNamespace(get=lambda gid: group if gid == 3 else None)
    
    services.User = FakeUser
    services.Group = FakeGroup
    services.db = make_fake_db()

    result = services.join_group_service("u7", 3)

    assert result is group
    assert group in user.groups
    services.db.session.commit.assert_called_once()


def test_join_group_service_returns_group_if_already_member():
    # Setup fake user already in group
    user = FakeUser(id="u8", username="grace", email="grace@example.com")
    
    class FakeGroup:
        query = None
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    group = FakeGroup(id=4, name="Existing Group")
    user.groups = [group]  # User is already in group

    # Setup queries
    FakeUser.query = SimpleNamespace(get=lambda uid: user if uid == "u8" else None)
    FakeGroup.query = SimpleNamespace(get=lambda gid: group if gid == 4 else None)
    
    services.User = FakeUser
    services.Group = FakeGroup
    services.db = make_fake_db()

    result = services.join_group_service("u8", 4)

    assert result is group
    assert services.db.session.commit.call_count == 0


def test_join_group_service_raises_when_user_not_found():
    FakeUser.query = SimpleNamespace(get=lambda uid: None)
    services.User = FakeUser

    with pytest.raises(Exception) as excinfo:
        services.join_group_service("missing", 1)
    assert "User with id missing does not exist" in str(excinfo.value)


def test_join_group_service_raises_when_group_not_found():
    # User exists but group doesn't
    user = FakeUser(id="u9")
    FakeUser.query = SimpleNamespace(get=lambda uid: user if uid == "u9" else None)
    
    class FakeGroup:
        query = None
    FakeGroup.query = SimpleNamespace(get=lambda gid: None)
    
    services.User = FakeUser
    services.Group = FakeGroup

    with pytest.raises(Exception) as excinfo:
        services.join_group_service("u9", 999)
    assert "Group with id 999 does not exist" in str(excinfo.value)




# -----------------------------
# Tests for get_all_groups
# -----------------------------
def test_get_all_groups_returns_all_groups():
    class FakeGroup:
        query = None
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    g1 = FakeGroup(id=1, name="Group A")
    g2 = FakeGroup(id=2, name="Group B")
    FakeGroup.query = SimpleNamespace(all=lambda: [g1, g2])
    services.Group = FakeGroup

    result = services.get_all_groups()
    
    assert result == [g1, g2]
    assert len(result) == 2
    assert result[0].name == "Group A"
    assert result[1].name == "Group B"


def test_get_all_groups_returns_empty_list_when_none():
    class FakeGroup:
        query = None
    FakeGroup.query = SimpleNamespace(all=lambda: [])
    services.Group = FakeGroup

    result = services.get_all_groups()
    assert result == []


# -----------------------------
# Tests for get_groups_for_user
# -----------------------------
def test_get_groups_for_user_returns_user_groups():
    # Setup fake user with groups
    class FakeGroup:
        def __init__(self, id, name):
            self.id = id
            self.name = name

    g1 = FakeGroup(1, "Group A")
    g2 = FakeGroup(2, "Group B")
    
    user = FakeUser(id="u10", username="harry", email="harry@example.com")
    user.groups = [g1, g2]

    FakeUser.query = SimpleNamespace(get=lambda uid: user if uid == "u10" else None)
    services.User = FakeUser

    result = services.get_groups_for_user("u10")
    
    assert result == [g1, g2]
    assert len(result) == 2
    assert result[0].name == "Group A"
    assert result[1].name == "Group B"


def test_get_groups_for_user_returns_empty_list_when_user_not_found():
    FakeUser.query = SimpleNamespace(get=lambda uid: None)
    services.User = FakeUser

    result = services.get_groups_for_user("missing")
    assert result == []


def test_get_groups_for_user_returns_empty_list_when_user_has_no_groups():
    user = FakeUser(id="u11", username="ian", email="ian@example.com")
    user.groups = []
    
    FakeUser.query = SimpleNamespace(get=lambda uid: user if uid == "u11" else None)
    services.User = FakeUser

    result = services.get_groups_for_user("u11")
    assert result == []

# -----------------------------
# Entity-specific validation tests
# -----------------------------
def test_update_task_service_validates_status_transition():
    task = FakeTask(id="t3", status="todo")
    FakeTask.query = SimpleNamespace(get=lambda tid: task)
    services.Task = FakeTask
    services.db = make_fake_db()

    # Valid transition todo -> in_progress
    services.update_task_service("t3", {"status": "in_progress"})
    assert task.status == "in_progress"

    # Invalid transition in_progress -> cancelled
    with pytest.raises(ValueError) as excinfo:
        services.update_task_service("t3", {"status": "cancelled"})
    assert "Invalid status transition" in str(excinfo.value)

def test_create_task_service_validates_due_date():
    data = {
        "title": "Past Task",
        "deadline": "2020-01-01",  # Past date
        "kind": "homework",
        "priority": "high"
    }
    
    FakeTask.query = MockQuery()
    services.Task = FakeTask
    services.db = make_fake_db()
    
    with pytest.raises(ValueError) as excinfo:
        services.create_task_service(data)
    assert "Deadline cannot be in the past" in str(excinfo.value)

def test_update_task_service_validates_progress():
    task = FakeTask(id="t4", progress=50)
    FakeTask.query = SimpleNamespace(get=lambda tid: task)
    services.Task = FakeTask
    services.db = make_fake_db()

    # Invalid progress value
    with pytest.raises(ValueError) as excinfo:
        services.update_task_service("t4", {"progress": 101})
    assert "Progress must be between 0 and 100" in str(excinfo.value)

def test_task_priority_management():
    task = FakeTask(id="t5", priority="low")
    FakeTask.query = SimpleNamespace(get=lambda tid: task)
    services.Task = FakeTask
    services.db = make_fake_db()

    # Valid priority update
    services.update_task_service("t5", {"priority": "high"})
    assert task.priority == "high"

    # Invalid priority value
    with pytest.raises(ValueError) as excinfo:
        services.update_task_service("t5", {"priority": "super-high"})
    assert "Invalid priority value" in str(excinfo.value)

# Fix the task assignment validation test
def test_task_assignment_validation():
    # Create two users - one in group, one not
    group_user = FakeUser(id="u12")
    other_user = FakeUser(id="other-user")
    group = SimpleNamespace(id=5)
    group_user.groups = [group]
    other_user.groups = []  # not in the group
    
    task = FakeTask(
        id="t6", 
        group_id=5,
        assignee=None
    )
    
    # Setup query to return either user based on id
    FakeUser.query = SimpleNamespace(
        get=lambda uid: {
            "u12": group_user,
            "other-user": other_user
        }.get(uid)
    )
    FakeTask.query = SimpleNamespace(get=lambda tid: task)
    services.Task = FakeTask
    services.User = FakeUser
    services.db = make_fake_db()

    # First verify we can assign to user in group
    services.update_task_service("t6", {"assignee": "u12"})
    assert task.assignee == "u12"

    # Then verify we cannot assign to user not in group
    with pytest.raises(ValueError) as excinfo:
        services.update_task_service("t6", {"assignee": "other-user"})
    assert "Assignee must be member of the group" in str(excinfo.value)