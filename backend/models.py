from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# -----------------------------
# Association Object for Many-to-Many with extra data: Users <-> Groups
# -----------------------------
class GroupMembership(db.Model):
    __tablename__ = 'group_memberships'
    user_id = db.Column(db.String(50), db.ForeignKey('users.id'), primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), primary_key=True)
    role = db.Column(db.String(50), nullable=False, default='member')  # z.B. 'member', 'admin'

    # Relationships to User and Group
    user = db.relationship('User', back_populates='group_memberships')
    group = db.relationship('Group', back_populates='group_memberships')


# -----------------------------
# User Model
# -----------------------------
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.String(50), primary_key=True)  # Keycloak "sub"
    username = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), nullable=False)
    birthday = db.Column(db.Date, nullable=True)
    faculty = db.Column(db.String(100), nullable=True)

    # One-to-many: memberships
    group_memberships = db.relationship('GroupMembership', back_populates='user', cascade='all, delete-orphan')

    # One-to-many: tasks created by this user
    tasks = db.relationship('Task', back_populates='user', cascade='all, delete-orphan')


# -----------------------------
# Group Model
# -----------------------------
class Group(db.Model):
    __tablename__ = 'groups'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    group_number = db.Column(db.Integer, nullable=False)
    invite_link = db.Column(db.String(200), nullable=False)

    # One-to-many: memberships
    group_memberships = db.relationship('GroupMembership', back_populates='group', cascade='all, delete-orphan')

    # One-to-many: tasks belonging to this group
    tasks = db.relationship('Task', back_populates='group', cascade='all, delete-orphan')


# -----------------------------
# Task Model
# -----------------------------
class Task(db.Model):
    __tablename__ = 'tasks'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    deadline = db.Column(db.Date, nullable=False)
    kind = db.Column(db.String(50), nullable=False)
    priority = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='todo')
    progress = db.Column(db.Integer, nullable=False, default=0)
    assignee = db.Column(db.String(100), nullable=True)
    notes = db.Column(db.Text, nullable=True)

    # Foreign keys
    user_id = db.Column(db.String(50), db.ForeignKey('users.id'), nullable=True)
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=True)

    # Relationships
    user = db.relationship('User', back_populates='tasks')
    group = db.relationship('Group', back_populates='tasks')
