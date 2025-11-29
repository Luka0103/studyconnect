from datetime import datetime, date
from sqlalchemy import and_
from .models import db, User, Group, Task, GroupMembership

VALID_PRIORITIES = ['low', 'medium', 'high']
VALID_STATUSES = {
    'todo': ['in_progress'],
    'in_progress': ['done', 'blocked'],
    'blocked': ['in_progress'],
    'done': []
}


class UserService:
    """
    Service-Klasse für Benutzerlogik, um die Anforderungen von Übung 6.2 zu erfüllen.
    Abhängigkeiten werden über den Konstruktor injiziert, um Mocking zu ermöglichen.
    """
    def __init__(self, db_session, keycloak_admin_client):
        self.db = db_session
        self.keycloak_admin = keycloak_admin_client

    def register_user(self, user_data):
        """Implementiert User Registration & Password Validation."""
        password = user_data.get("password")

        # Anforderung aus 6.2: Password validation rules
        if not password or len(password) < 8:
            raise ValueError("Password must be at least 8 characters long.")

        # 1. User in Keycloak anlegen
        new_user_id = self.keycloak_admin.create_user(user_data['keycloak_payload'])
        self.keycloak_admin.set_user_password(new_user_id, password, temporary=False)
        self.keycloak_admin.update_user(new_user_id, {"requiredActions": []})

        # 2. User in lokaler DB anlegen
        birthday_date = datetime.strptime(user_data['birthday'], "%Y-%m-%d").date() if user_data.get('birthday') else None
        new_user = User(
            id=new_user_id,
            username=user_data['username'],
            email=user_data['email'],
            birthday=birthday_date,
            faculty=user_data.get('faculty')
        )
        self.db.add(new_user)
        self.db.commit()
        return new_user

    def get_or_create_user_from_keycloak(self, keycloak_userinfo):
        """Stellt sicher, dass ein Keycloak-Benutzer in der lokalen DB existiert."""
        user_id = keycloak_userinfo.get("sub")
        if not user_id:
            raise Exception("Missing Keycloak user ID (sub)")

        user = self.db.get(User, user_id)
        if not user:
            username = keycloak_userinfo.get("preferred_username") or keycloak_userinfo.get("email")
            email = keycloak_userinfo.get("email")
            user = User(id=user_id, username=username, email=email)
            self.db.add(user)
            self.db.commit()
        return user

    def update_user(self, user_id, data):
        """Aktualisiert die Daten eines Benutzers in der lokalen DB."""
        user = self.db.get(User, user_id)
        if not user:
            raise Exception(f"User with id {user_id} not found.")

        # Felder aktualisieren, die in den Daten vorhanden sind
        if 'username' in data:
            user.username = data['username']
        if 'email' in data:
            user.email = data['email']
        if 'faculty' in data:
            user.faculty = data['faculty']
        if 'birthday' in data and data['birthday']:
            user.birthday = datetime.strptime(data['birthday'], "%Y-%m-%d").date()

        self.db.commit()
        return user

# -----------------------------
# User Services
# -----------------------------
def get_user_service(user_id: str):
    """Get a user by ID or raise."""
    user = db.session.get(User, user_id)
    if not user:
        raise Exception(f"User with id {user_id} does not exist")
    return user


# -----------------------------
# Task Services
# -----------------------------
def create_task_service(data):
    # Validate deadline
    deadline_date = datetime.strptime(data['deadline'], '%Y-%m-%d').date()
    if deadline_date < date.today():
        raise ValueError("Deadline cannot be in the past")

    user_id = data.get('user_id')  # string
    group_id = data.get('group_id')

    # check for existing duplicate task
    existing_task = Task.query.filter(
        and_(
            Task.title == data['title'],
            Task.deadline == deadline_date,
            Task.user_id == user_id,
            Task.group_id == group_id
        )
    ).first()
    if existing_task:
        return existing_task

    task = Task(
        title=data['title'],
        deadline=deadline_date,
        kind=data['kind'],
        priority=data['priority'],
        status=data.get('status', 'todo'),
        user_id=user_id,
        group_id=group_id,
        assignee=data.get('assignee'),
        notes=data.get('notes'),
        progress=data.get('progress', 0)
    )
    db.session.add(task)
    db.session.commit()
    return task


def update_task_service(task_id, data):
    task = db.session.get(Task, task_id)
    if not task:
        raise Exception(f"Task with id {task_id} does not exist")

    # Validate status transition
    if 'status' in data:
        current_status = task.status
        new_status = data['status']
        if new_status not in VALID_STATUSES.get(current_status, []):
            raise ValueError(f"Invalid status transition from {current_status} to {new_status}")

    # Validate progress
    if 'progress' in data:
        progress = data['progress']
        if not (0 <= progress <= 100):
            raise ValueError("Progress must be between 0 and 100")

    # Validate priority
    if 'priority' in data:
        if data['priority'] not in VALID_PRIORITIES:
            raise ValueError(f"Invalid priority value. Must be one of: {VALID_PRIORITIES}")

    # Validate assignee
    if 'assignee' in data:
        assignee = db.session.get(User, data['assignee'])
        if not assignee:
            raise ValueError("Assignee user not found")
        if task.group_id and task.group_id not in [m.group.id for m in assignee.group_memberships]:
            raise ValueError("Assignee must be member of the group")

    # Update fields
    for field in ['title', 'kind', 'priority', 'status', 'user_id', 'group_id', 'assignee', 'notes', 'progress']:
        if field in data:
            setattr(task, field, data[field])

    if 'deadline' in data:
        deadline_date = datetime.strptime(data['deadline'], '%Y-%m-%d').date()
        if deadline_date < date.today():
            raise ValueError("Deadline cannot be in the past")
        task.deadline = deadline_date

    db.session.commit()
    return task


def get_tasks_for_user(user_id: str):
    user = db.session.get(User, user_id)
    if not user:
        return []

    group_ids = [m.group.id for m in user.group_memberships]
    return Task.query.filter(
        (Task.user_id == user_id) | (Task.group_id.in_(group_ids))
    ).all()


def get_all_tasks():
    return Task.query.all()


# -----------------------------
# Group Services
# -----------------------------
def create_group_service(data, creator_id: str):
    group = Group(
        name=data['name'],
        description=data.get('description'),
        group_number=data['groupNumber'],
        invite_link=data['inviteLink']
    )
    db.session.add(group)
    # Der Ersteller wird automatisch zum Admin der Gruppe
    membership = GroupMembership(user_id=creator_id, group=group, role='admin')
    db.session.add(membership)
    db.session.commit()
    return group


def join_group_service(user_id: str, group_id: int):
    user = db.session.get(User, user_id)
    group = db.session.get(Group, group_id)

    if not user:
        raise Exception(f"User with id {user_id} does not exist")
    if not group:
        raise Exception(f"Group with id {group_id} does not exist")

    # Prüfen, ob eine Mitgliedschaft bereits existiert
    existing_membership = db.session.query(GroupMembership).filter_by(user_id=user_id, group_id=group_id).first()
    if existing_membership:
        return group

    membership = GroupMembership(user_id=user_id, group_id=group_id, role='member')
    db.session.add(membership)
    db.session.commit()
    return group


def get_all_groups():
    return Group.query.all()


def get_groups_for_user(user_id: str):
    user = db.session.get(User, user_id)
    if not user:
        return []
    # Gibt eine Liste von Group-Objekten zurück, in denen der Benutzer Mitglied ist
    return [membership.group for membership in user.group_memberships]
