import os
import sys
from types import SimpleNamespace, ModuleType
from unittest.mock import Mock, MagicMock
from datetime import date, datetime
import pytest
from backend import services

# Mock classes for testing
class DummyExpr:
    def __or__(self, other):
        return self
class DummyColumn:
    def __eq__(self, other):
        return DummyExpr

class FakeUser:
    query = None
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.username = kwargs.get('username')
        self.email = kwargs.get('email')
        self.birthday = kwargs.get('birthday')
        self.faculty = kwargs.get('faculty')
        self.group_memberships = []

def make_fake_db():
    session = SimpleNamespace(add=Mock(), commit=Mock(), get=Mock(), query=MagicMock())
    return SimpleNamespace(session=session)

# Install a fake 'models' module into sys.modules so services can import it
fake_models = ModuleType("models")
fake_models.db = make_fake_db()
fake_models.User = FakeUser
fake_models.Group = SimpleNamespace()
fake_models.Task = SimpleNamespace()
fake_models.GroupMembership = SimpleNamespace()
sys.modules["models"] = fake_models

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

# -----------------------------
# Tests for get_user_service
# -----------------------------
def test_get_user_service_returns_user_when_exists():
    existing = FakeUser(id="u10", username="carol", email="carol@example.com")
    services.User = FakeUser
    services.db = make_fake_db()
    services.db.session.get.return_value = existing

    result = services.get_user_service("u10")

    assert result is existing

def test_get_user_service_raises_when_not_exists():
    services.User = FakeUser
    services.db = make_fake_db()
    services.db.session.get.return_value = None

    with pytest.raises(Exception) as excinfo:
        services.get_user_service("missing")
    assert "does not exist" in str(excinfo.value)


# -----------------------------
# Tests for create_task_service (fixed: provide class-level attributes used in comparisons)
# -----------------------------
def test_create_task_service_returns_existing_task(monkeypatch):
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

    class FakeDate(date):
        @classmethod
        def today(cls):
            return date(2025, 1, 1)
    monkeypatch.setattr(services, "date", FakeDate, raising=False)

    result = services.create_task_service(data)
    assert result is existing_task
    assert services.db.session.add.call_count == 0
    assert services.db.session.commit.call_count == 0


def test_create_task_service_creates_and_commits_new_task(monkeypatch):
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

    class FakeDate(date):
        @classmethod
        def today(cls):
            return date(2025, 1, 1)
    monkeypatch.setattr(services, "date", FakeDate, raising=False)

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
def test_update_task_service_updates_fields_and_deadline(monkeypatch):
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

    services.Task = FakeTask
    services.db = make_fake_db()
    services.db.session.get.return_value = existing

    class FakeDate(date):
        @classmethod
        def today(cls):
            return date(2025, 1, 1)
    monkeypatch.setattr(services, "date", FakeDate, raising=False)

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

    services.Task = FakeTask
    services.db = make_fake_db()
    services.db.session.get.return_value = None

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
    user.group_memberships = [SimpleNamespace(group=group)]
    services.User = FakeUser
    services.db = make_fake_db()

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
    services.db.session.get.return_value = user

    result = services.get_tasks_for_user("u5")
    assert result == [task_user, task_group]

def test_get_tasks_for_user_returns_empty_list_when_user_missing():
    """Tests that get_tasks_for_user raises an error if the user is not found."""
    services.User = FakeUser
    services.db = make_fake_db()
    services.db.session.get.return_value = None

    with pytest.raises(Exception, match="does not exist"):
        services.get_tasks_for_user("nope")

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
def test_create_group_service_creates_and_commits_new_group():
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
        _sa_instance_state = MagicMock() # Use MagicMock to handle subscripting

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

    result = services.create_group_service(data, creator_id="creator-1")

    assert isinstance(result, FakeGroup)
    assert result.name == "New Study Group"
    assert result.description == "A fresh group"
    assert result.group_number == "G999"
    assert result.invite_link == "newlink999" 

    assert services.db.session.add.call_count == 2 # Group and Membership
    assert services.db.session.commit.call_count == 1


def test_join_group_service_adds_user_to_group():
    class FakeGroup:
        group_number = DummyColumn()
        invite_link = DummyColumn()
        query = None
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
        _sa_instance_state = MagicMock()

    # Setup fake user and group
    user = FakeUser(id="u7", username="frank", email="frank@example.com")
    group = FakeGroup(id=3, name="Test Group")

    # Setup queries
    services.User = FakeUser
    services.Group = FakeGroup
    services.db = make_fake_db()
    services.db.session.get.side_effect = [user, group] # First call returns user, second group
    services.db.session.query.return_value.filter_by.return_value.first.return_value = None # Configure the mock chain

    result = services.join_group_service("u7", 3)

    assert result is group
    assert services.db.session.add.call_count == 1
    services.db.session.commit.assert_called_once()


def test_join_group_service_returns_group_if_already_member():
    # Setup fake user already in group
    user = FakeUser(id="u8", username="grace", email="grace@example.com")
    
    class FakeGroup:
        query = None
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    services.User = FakeUser
    services.Group = FakeGroup
    services.db = make_fake_db()
    services.db.session.get.side_effect = [user, FakeGroup(id=4)]
    services.db.session.query.return_value.filter_by.return_value.first.return_value = True # Configure the mock chain

    result = services.join_group_service("u8", 4)

    assert result is not None
    assert services.db.session.commit.call_count == 0


def test_join_group_service_raises_when_user_not_found():
    services.User = FakeUser
    services.db = make_fake_db()
    services.db.session.get.return_value = None

    with pytest.raises(Exception) as excinfo:
        services.join_group_service("missing", 1)
    assert "User with id missing does not exist" in str(excinfo.value)


def test_join_group_service_raises_when_group_not_found():
    user = FakeUser(id="u9")
    class FakeGroup:
        query = None

    services.User = FakeUser
    services.Group = FakeGroup
    services.db = make_fake_db()
    # First get (user) succeeds, second (group) fails
    services.db.session.get.side_effect = [user, None]

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
    user.group_memberships = [SimpleNamespace(group=g1), SimpleNamespace(group=g2)]

    services.User = FakeUser
    services.db = make_fake_db()
    services.db.session.get.return_value = user

    result = services.get_groups_for_user("u10")
    
    assert result == [g1, g2]
    assert len(result) == 2


def test_get_groups_for_user_returns_empty_list_when_user_not_found():
    """Tests that get_groups_for_user raises an error if the user is not found."""
    services.User = FakeUser
    services.db = make_fake_db()
    services.db.session.get.return_value = None

    with pytest.raises(Exception, match="does not exist"):
        services.get_groups_for_user("missing")


def test_get_groups_for_user_returns_empty_list_when_user_has_no_groups():
    user = FakeUser(id="u11", username="ian", email="ian@example.com")
    services.User = FakeUser
    services.db = make_fake_db()
    services.db.session.get.return_value = user

    result = services.get_groups_for_user("u11")
    assert result == []

# -----------------------------
# Entity-specific validation tests
# -----------------------------
def test_update_task_service_validates_status_transition():
    task = FakeTask(id="t3", status="todo")
    services.Task = FakeTask
    services.db = make_fake_db()
    services.db.session.get.return_value = task

    # Valid transition todo -> in_progress
    services.update_task_service("t3", {"status": "in_progress"})
    assert task.status == "in_progress"

    # Invalid transition in_progress -> cancelled
    with pytest.raises(ValueError) as excinfo:
        services.update_task_service("t3", {"status": "cancelled"})
    assert "Invalid status transition" in str(excinfo.value)

def test_create_task_service_validates_due_date(monkeypatch):
    data = {
        "title": "Past Task",
        "deadline": "2020-01-01",  # Past date
        "kind": "homework",
        "priority": "high"
    }
    
    services.Task = FakeTask
    services.db = make_fake_db()

    class FakeDate(date):
        @classmethod
        def today(cls):
            return date(2024, 1, 1)
    monkeypatch.setattr(services, "date", FakeDate, raising=False)
    
    with pytest.raises(ValueError) as excinfo:
        services.create_task_service(data)
    assert "Deadline cannot be in the past" in str(excinfo.value)

def test_update_task_service_validates_progress():
    task = FakeTask(id="t4", progress=50)
    services.Task = FakeTask
    services.db = make_fake_db()
    services.db.session.get.return_value = task

    # Invalid progress value
    with pytest.raises(ValueError) as excinfo:
        services.update_task_service("t4", {"progress": 101})
    assert "Progress must be between 0 and 100" in str(excinfo.value)

def test_task_priority_management():
    task = FakeTask(id="t5", priority="low")
    services.Task = FakeTask
    services.db = make_fake_db()
    services.db.session.get.return_value = task

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
    group_user.group_memberships = [SimpleNamespace(group=SimpleNamespace(id=5))]
    
    task = FakeTask(
        id="t6", 
        group_id=5,
        assignee=None
    )
    
    # Setup query to return either user based on id
    services.Task = FakeTask
    services.User = FakeUser
    services.db = make_fake_db()
    services.db.session.get.side_effect = lambda model, id: {
        "t6": task,
        "u12": group_user,
        "other-user": other_user
    }.get(id)

    # First verify we can assign to user in group
    services.update_task_service("t6", {"assignee": "u12"})
    assert task.assignee == "u12"

    # Then verify we cannot assign to user not in group
    with pytest.raises(ValueError) as excinfo:
        services.update_task_service("t6", {"assignee": "other-user"})
    assert "Assignee must be member of the group" in str(excinfo.value)