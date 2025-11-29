from datetime import datetime, date
from sqlalchemy import and_
from .models import db, User, Group, Task, GroupMembership

VALID_PRIORITIES = ['low', 'medium', 'high']
VALID_STATUSES = {
    'todo': ['in_progress'],
    'in_progress': ['done', 'blocked', 'todo'],
    'blocked': ['in_progress'],
    'done': ['in_progress', 'todo']
}


class UserService:
    """
    Service class for user logic to meet the requirements of Exercise 6.2.
    Dependencies are injected via the constructor to allow for mocking.
    """
    def __init__(self, db_session, keycloak_admin_client):
        self.db = db_session
        self.keycloak_admin = keycloak_admin_client

    def register_user(self, user_data):
        """Implements user registration & password validation."""
        password = user_data.get("password")

        # Requirement from 6.2: Password validation rules
        if not password or len(password) < 8:
            raise ValueError("Password must be at least 8 characters long.")

        # 1. Create user in Keycloak
        new_user_id = self.keycloak_admin.create_user(user_data['keycloak_payload'])
        self.keycloak_admin.set_user_password(new_user_id, password, temporary=False)
        self.keycloak_admin.update_user(new_user_id, {"requiredActions": []})

        # 2. Create user in local DB
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

    def login(self, username, password):
        """Logs a user in via Keycloak and returns a token."""
        from backend.api import keycloak_openid
        # This will call the patched keycloak_openid in tests
        token = keycloak_openid.token(username, password)
        return token

    def get_or_create_user_from_keycloak(self, keycloak_userinfo):
        """Ensures that a Keycloak user exists in the local DB."""
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
        """Updates a user's data in the local DB."""
        user = self.db.get(User, user_id)
        if not user:
            raise Exception(f"User with id {user_id} not found.")

        # Update fields that are present in the data
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


def update_task_service(task_id, data, editor_user_id=None):
    task = db.session.get(Task, task_id)
    if not task:
        raise Exception(f"Task with id {task_id} does not exist")

    # Pre-cleanup: The 'expired' status is a pure display state of the frontend
    # and must never be written to or validated by the database.
    if data.get('status') == 'expired':
        del data['status']

    # Validate status transition
    if 'status' in data:
        # Normalize both the current and the new status to resolve inconsistencies
        current_status = task.status.lower().replace("inprogress", "in_progress").replace("expired", "todo")
        # Convert the received status to lowercase to avoid case issues (e.g., inProgress vs. in_progress)
        new_status = data['status'].lower().replace("inprogress", "in_progress")
        # Save the corrected version back to the data so it is stored correctly
        data['status'] = new_status

        # Only validate the transition if the status actually changes.
        if new_status != current_status and new_status not in VALID_STATUSES.get(current_status, []):
            raise ValueError(f"Invalid status transition from {current_status} to {new_status}")
        
        # Prevent a past-due task from being started
        if new_status == 'in_progress' and task.deadline < date.today():
            raise ValueError("Cannot start a task that is past its deadline.")
        
        # If a task is set to 'done', automatically set its progress to 100.
        if new_status == 'done':
            task.progress = 100

    # Validate progress
    if 'progress' in data:
        progress = data['progress']
        if not (0 <= progress <= 100):
            raise ValueError("Progress must be between 0 and 100")

    # Validate priority
    if 'priority' in data:
        if data['priority'] not in VALID_PRIORITIES:
            raise ValueError(f"Invalid priority value. Must be one of: {VALID_PRIORITIES}")

    # Validate group assignment permission
    if data.get('group_id') is not None:
        if not editor_user_id:
            raise PermissionError("User ID is required to assign a task to a group.")
        
        editor = db.session.get(User, editor_user_id)
        if not any(m.group_id == data['group_id'] for m in editor.group_memberships):
            raise PermissionError("You can only assign tasks to groups you are a member of.")

    # Validate assignee
    if data.get('assignee') is not None:
        assignee = db.session.get(User, data['assignee'])
        if not assignee:
            raise ValueError("Assignee user not found")
        
        # The group_id to check against is either the new one from `data` or the existing one on the task
        target_group_id = data.get('group_id', task.group_id)
        if target_group_id and not any(m.group_id == target_group_id for m in assignee.group_memberships):
            raise ValueError("Assignee must be member of the group")

    # Update fields
    for field in ['title', 'kind', 'priority', 'status', 'user_id', 'group_id', 'assignee', 'notes', 'progress']:
        if field in data and data[field] is not None:
            setattr(task, field, data[field])
    
    if 'group_id' in data: # Explicitly handle group_id to allow 'None'
        task.group_id = data['group_id']

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
        raise Exception(f"User with id {user_id} does not exist")

    # 1. Find all groups the user is a member of.
    group_ids = [m.group.id for m in user.group_memberships]

    # 2. Fetch all tasks that are either assigned to the user personally (user_id matches)
    #    OR are assigned to one of the user's groups (group_id is in their group list).
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
    # The creator automatically becomes the admin of the group
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

    # Check if a membership already exists
    existing_membership = db.session.query(GroupMembership).filter_by(user_id=user_id, group_id=group_id).first()
    if existing_membership:
        return group

    membership = GroupMembership(user_id=user_id, group_id=group_id, role='member')
    db.session.add(membership)
    db.session.commit()
    return group

def leave_group_service(user_id: str, group_id: int):
    """Removes a user's membership from a group."""
    membership = db.session.query(GroupMembership).filter_by(user_id=user_id, group_id=group_id).first()

    if not membership:
        raise Exception("User is not a member of this group.")

    # If the user is the last admin, delete the entire group.
    if membership.role == 'admin':
        other_admins = db.session.query(GroupMembership).filter(GroupMembership.group_id == group_id, GroupMembership.role == 'admin', GroupMembership.user_id != user_id).count()
        if other_admins == 0:
            group_to_delete = db.session.get(Group, group_id)
            if group_to_delete:
                db.session.delete(group_to_delete)
                db.session.commit()
                return # Exit after deleting the group

    db.session.delete(membership)
    db.session.commit()

def promote_to_admin_service(promoter_id: str, user_to_promote_id: str, group_id: int):
    """Promotes a user to admin within a group, checking for promoter's admin rights."""
    # Check if the person doing the promotion is an admin
    promoter_membership = db.session.query(GroupMembership).filter_by(user_id=promoter_id, group_id=group_id).first()
    if not promoter_membership or promoter_membership.role != 'admin':
        raise PermissionError("Only admins can promote other members.")

    # Find the membership of the user to be promoted
    membership_to_update = db.session.query(GroupMembership).filter_by(user_id=user_to_promote_id, group_id=group_id).first()
    if not membership_to_update:
        raise Exception("User to be promoted is not a member of this group.")

    # Update the role and commit
    membership_to_update.role = 'admin'
    db.session.commit()
    return membership_to_update

def kick_user_service(kicker_id: str, user_to_kick_id: str, group_id: int):
    """Removes a user from a group, with admin permission checks."""
    # Check if the person doing the kicking is an admin
    kicker_membership = db.session.query(GroupMembership).filter_by(user_id=kicker_id, group_id=group_id).first()
    if not kicker_membership or kicker_membership.role != 'admin':
        raise PermissionError("Only admins can kick members.")

    # Find the membership of the user to be kicked
    membership_to_kick = db.session.query(GroupMembership).filter_by(user_id=user_to_kick_id, group_id=group_id).first()
    if not membership_to_kick:
        raise Exception("User to be kicked is not a member of this group.")

    # Prevent an admin from kicking another admin or themselves
    if membership_to_kick.role == 'admin':
        raise PermissionError("Admins cannot kick other admins.")
    if kicker_id == user_to_kick_id:
        raise PermissionError("You cannot kick yourself. Use the 'Leave Group' feature.")

    db.session.delete(membership_to_kick)
    db.session.commit()

def get_all_groups():
    return Group.query.all()


def get_groups_for_user(user_id: str):
    user = db.session.get(User, user_id)
    if not user:
        raise Exception(f"User with id {user_id} does not exist")
    # Returns a list of Group objects that the user is a member of
    return [membership.group for membership in user.group_memberships]
