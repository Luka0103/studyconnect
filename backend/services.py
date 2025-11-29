from datetime import datetime, date
from sqlalchemy import and_
from .models import db, User, Group, Task, GroupMember
from random import choice


VALID_PRIORITIES = ['low', 'medium', 'high']
VALID_STATUSES = {
    "todo": ["inProgress", "done", "expired"],
    "inProgress": ["todo", "done", "expired"],
    "done": ["todo", "inProgress", "expired"],
    "expired": ["todo", "inProgress", "done"],
}

# -----------------------------
# User Role Helpers
# -----------------------------
def is_group_admin(user_id, group_id):
    membership = GroupMember.query.filter_by(user_id=user_id, group_id=group_id).first()
    return membership and membership.role == "admin"


# -----------------------------
# User Services
# -----------------------------
def get_or_create_user_from_keycloak(kc_userinfo):
    user_id = kc_userinfo.get("sub")
    username = kc_userinfo.get("preferred_username")
    email = kc_userinfo.get("email")

    if not user_id:
        raise Exception("Missing Keycloak user ID")

    user = User.query.get(user_id)
    if not user:
        user = User(id=user_id, username=username, email=email)
        db.session.add(user)
        db.session.commit()
    return user


def update_user_service(user_id, data):
    user = User.query.get(user_id)
    if not user:
        raise Exception("User not found")

    for field in ["username", "email", "faculty"]:
        if field in data:
            setattr(user, field, data[field])

    if "birthday" in data:
        user.birthday = datetime.strptime(data["birthday"], "%Y-%m-%d").date()

    db.session.commit()
    return user


# -----------------------------
# Task Services
# -----------------------------
def create_task_service(data):
    deadline_date = datetime.strptime(data["deadline"], "%Y-%m-%d").date()
    if deadline_date < date.today():
        raise ValueError("Deadline cannot be in the past")

    user_id = data.get("user_id")
    group_id = data.get("group_id")

    # Only admins can create group tasks
    if group_id and not is_group_admin(user_id, group_id):
        raise Exception("Only admins can create tasks for this group")

    task = Task(
        title=data["title"],
        deadline=deadline_date,
        kind=data["kind"],
        priority=data["priority"],
        status=data.get("status", "todo"),
        user_id=user_id,
        group_id=group_id,
        assignee=data.get("assignee"),
        notes=data.get("notes"),
        progress=data.get("progress", 0)
    )
    db.session.add(task)
    db.session.commit()
    return task


def update_task_service(task_id, data, current_user_id):
    task = Task.query.get(task_id)
    if not task:
        raise Exception("Task not found")

    if task.group_id and not is_group_admin(current_user_id, task.group_id):
        raise Exception("Only admins can update tasks for this group")

    if "deadline" in data:
        deadline_date = datetime.strptime(data["deadline"], "%Y-%m-%d").date()
        if deadline_date < date.today():
            raise ValueError("Deadline cannot be in the past")
        task.deadline = deadline_date

    if "priority" in data and data["priority"] not in VALID_PRIORITIES:
        raise ValueError("Invalid priority")

    if "progress" in data and not (0 <= data["progress"] <= 100):
        raise ValueError("Progress must be 0–100")

    for field in ["title", "kind", "priority", "status", "notes", "assignee", "progress"]:
        if field in data:
            setattr(task, field, data[field])

    if "group_id" in data:
        task.group_id = data["group_id"]

    db.session.commit()
    return task



def get_tasks_for_user(user_id):
    user = User.query.get(user_id)
    if not user:
        return []

    group_ids = [gm.group_id for gm in user.group_memberships]

    # Query tasks assigned to the user or belonging to user's groups
    tasks = Task.query.filter(
        (Task.user_id == user_id) | (Task.group_id.in_(group_ids))
    ).all()

    # Remove duplicates by task ID
    unique_tasks = {task.id: task for task in tasks}.values()
    return list(unique_tasks)



# -----------------------------
# Group Services
# -----------------------------
def create_group_service(data, creator_id=None):
    group = Group(
        name=data["name"],
        description=data.get("description"),
        group_number=data["groupNumber"],
        invite_link=data["inviteLink"]
    )
    db.session.add(group)
    db.session.commit()

    # Auto-add creator as member & admin
    if creator_id:
        gm = GroupMember(user_id=creator_id, group_id=group.id, role="admin")
        db.session.add(gm)
        db.session.commit()

    return group


def join_group_service(user_id, group_id):
    if GroupMember.query.filter_by(user_id=user_id, group_id=group_id).first():
        return Group.query.get(group_id)

    gm = GroupMember(user_id=user_id, group_id=group_id, role="member")
    db.session.add(gm)
    db.session.commit()
    return Group.query.get(group_id)


def kick_from_group_service(admin_id, user_id, group_id):
    if not is_group_admin(admin_id, group_id):
        raise Exception("Only admins can remove users")

    membership = GroupMember.query.filter_by(user_id=user_id, group_id=group_id).first()
    if membership:
        db.session.delete(membership)
        db.session.commit()


def promote_to_admin_service(admin_id, user_id, group_id):
    if not is_group_admin(admin_id, group_id):
        raise Exception("Only admins can promote users")

    membership = GroupMember.query.filter_by(user_id=user_id, group_id=group_id).first()
    if not membership:
        raise Exception("User not in group")

    membership.role = "admin"
    db.session.commit()

    
def get_all_groups():
    return Group.query.all()

def get_groups_for_user(user_id: str):
    """
    Return all groups the user belongs to.
    """
    user = User.query.get(user_id)
    if not user:
        return []

    return user.groups  

# -----------------------------
# Leave Group Service
# -----------------------------
def leave_group_service(user_id, group_id):
    membership = GroupMember.query.filter_by(user_id=user_id, group_id=group_id).first()
    if not membership:
        raise Exception("User is not a member of this group")

    is_admin = membership.role == "admin"

    # Remove the user from the group
    db.session.delete(membership)
    db.session.commit()

    if is_admin:
        # Check if there are any remaining admins
        remaining_admins = GroupMember.query.filter_by(group_id=group_id, role="admin").all()
        if not remaining_admins:
            # Assign a random member as new admin if available
            remaining_members = GroupMember.query.filter_by(group_id=group_id).all()
            if remaining_members:
                new_admin = choice(remaining_members)
                new_admin.role = "admin"
                db.session.commit()