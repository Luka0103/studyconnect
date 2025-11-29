from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from dotenv import load_dotenv
from keycloak import KeycloakOpenID
from keycloak.exceptions import KeycloakError
from .models import User, Group, db
from .services import (
    create_task_service, create_group_service,
    get_tasks_for_user, get_groups_for_user,
    join_group_service, update_task_service, get_all_groups,
    UserService
)
from .auth import create_user, get_user_by_id, keycloak_protect, keycloak_admin, set_user_password, update_user

# -----------------------------
# App Initialization
# -----------------------------
app = Flask(__name__)
load_dotenv()
CORS(app, resources={r"/*": {"origins": "*"}})

# -----------------------------
# PostgreSQL Configuration
# -----------------------------
POSTGRES_USER = os.getenv("POSTGRES_USER", "root")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "root")
POSTGRES_DB = os.getenv("POSTGRES_DB", "StudyConnect")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", 5432)

app.config['SQLALCHEMY_DATABASE_URI'] = (
    f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
    f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# -----------------------------
# Keycloak Client
# -----------------------------
keycloak_openid = KeycloakOpenID(
    server_url=os.getenv("KEYCLOAK_SERVER_URL"),
    client_id=os.getenv("KEYCLOAK_CLIENT_ID"),
    realm_name=os.getenv("KEYCLOAK_REALM"),
    client_secret_key=os.getenv("KEYCLOAK_CLIENT_SECRET"),
)

# -----------------------------
# Helpers
# -----------------------------
def task_to_dict(t):
    return {
        "id": t.id,
        "title": t.title,
        "deadline": t.deadline.isoformat() if t.deadline else None,
        "kind": t.kind,
        "priority": t.priority,
        "status": t.status,
        "progress": t.progress,
        "group": {"id": t.group.id, "name": t.group.name} if t.group else None,
        "assignee": t.assignee,
    }

def group_to_dict(g: Group, user_id: str = None):
    """
    Serialize a Group object, including the role of a specific user if provided.
    """
    user_role = None
    if user_id:
        membership = next((m for m in g.group_memberships if m.user_id == user_id), None)
        if membership:
            user_role = membership.role

    members = [m.user_id for m in g.group_memberships]

    return {
        "id": g.id,
        "name": g.name,
        "description": g.description,
        "groupNumber": g.group_number,
        "inviteLink": g.invite_link,
        "members": members,
        "memberCount": len(members),
        "role": user_role  # This is what the frontend needs
    }

# -----------------------------
# Populate all Keycloak users into local DB
# -----------------------------
def populate_keycloak_users():
    with app.app_context():
        try:
            keycloak_users = keycloak_admin.get_users()
            print(f"Found {len(keycloak_users)} Keycloak users.")
            created_count = 0
            for kc_user in keycloak_users:
                user_id = kc_user.get("id") or kc_user.get("sub")
                if not user_id:
                    continue
                existing_user = db.session.get(User, user_id)
                # Logik in den Service verschoben, um Konsistenz zu wahren
                # Hier rufen wir den Service auf, um den User anzulegen, falls er fehlt.
                user_service = UserService(db.session, keycloak_admin)
                user_service.get_or_create_user_from_keycloak({
                    "sub": user_id,
                    "preferred_username": kc_user.get("username"),
                    "email": kc_user.get("email")
                })
                created_count += 1
            print(f"Created {created_count} new users in local DB.")
        except Exception as e:
            print(f"Error populating users: {e}")

# -----------------------------
# POST Routes
# -----------------------------

# Authentication
@app.route("/api/login", methods=["POST"])
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400

    try:
        token = keycloak_openid.token(username, password)
        return jsonify({
            "access_token": token.get("access_token"),
            "refresh_token": token.get("refresh_token")
        }), 200
    except Exception as e:
        return jsonify({"error": "Login failed", "details": str(e)}), 401

@app.route("/api/refresh", methods=["POST"])
def refresh_token():
    data = request.json
    refresh_token = data.get("refresh_token")

    if not refresh_token:
        return jsonify({"error": "Missing refresh token"}), 400

    try:
        new_tokens = keycloak_openid.refresh_token(refresh_token)

        return jsonify({
            "access_token": new_tokens.get("access_token"),
            "refresh_token": new_tokens.get("refresh_token"),
        }), 200

    except Exception as e:
        return jsonify({
            "error": "Failed to refresh token",
            "details": str(e)
        }), 401

# User Registration
@app.route("/api/users/register", methods=["POST"])
def register_user():
    data = request.json
    first_name = data.get("firstName")
    last_name = data.get("lastName")
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")
    birthday = data.get("birthday")
    faculty = data.get("faculty")

    if not first_name or not last_name or not username or not email or not password:
        return jsonify({"error": "firstName, lastName, username, email, and password are required"}), 400

    try:
        # Service initialisieren mit den echten Abhängigkeiten
        user_service = UserService(db.session, keycloak_admin)

        # Daten für den Service vorbereiten
        user_data = {
            "username": username,
            "email": email,
            "password": password,
            "birthday": birthday,
            "faculty": faculty,
            "keycloak_payload": {
                "username": username,
                "email": email,
                "firstName": first_name,
                "lastName": last_name,
                "enabled": True,
                "emailVerified": True,
                "attributes": {
                    "faculty": faculty or "",
                    "birthday": birthday or ""
                }
            }
        }

        new_user = user_service.register_user(user_data)

        return jsonify({
            "message": "User registered successfully",
            "id": new_user.id,
            "username": new_user.username
        }), 201

    except Exception as e:
        return jsonify({"error": "Keycloak or internal error", "details": str(e)}), 500

# Task Creation
@app.route("/api/tasks", methods=["POST"])
@keycloak_protect
def create_task():
    data = request.json
    user_service = UserService(db.session, keycloak_admin)
    kc_user = user_service.get_or_create_user_from_keycloak(request.user)
    data["user_id"] = kc_user.id
    try:
        task = create_task_service(data)
        return jsonify({"message": "Task created", "task": task_to_dict(task)}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# Group Creation / Join / Leave / Promote / Kick
@app.route("/api/groups", methods=["POST"])
@keycloak_protect
def create_group():
    data = request.json
    try:
        user_service = UserService(db.session, keycloak_admin)
        kc_user = user_service.get_or_create_user_from_keycloak(request.user)
        group = create_group_service(data, creator_id=kc_user.id)
        return jsonify({
            "message": "Group created",
            "group": group_to_dict(group)
        }), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/groups/join", methods=["POST"])
@keycloak_protect
def join_group():
    data = request.json
    user_service = UserService(db.session, keycloak_admin)
    kc_user = user_service.get_or_create_user_from_keycloak(request.user)
    group_id = data.get("group_id")
    try:
        group = join_group_service(kc_user.id, group_id)
        return jsonify({
            "message": f"User {kc_user.id} joined group {group.name}",
            "group": group_to_dict(group)
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/groups/<int:group_id>/kick", methods=["POST"])
@keycloak_protect
def kick_user(group_id):
    # ... Implementierung mit Services ...
    return jsonify({"message": "Not implemented yet"}), 501

# -----------------------------
# GET Routes
# -----------------------------
user_service = UserService(db.session, keycloak_admin)

# Users
@app.route("/api/users/<string:user_id>", methods=["GET"])
@keycloak_protect
def get_user(user_id):
    try:
        user = User.query.get(user_id)
        user_service = UserService(db.session, keycloak_admin)
        if not user:
            auth_header = request.headers.get("Authorization")
            token = auth_header.split()[1]
            kc_userinfo = keycloak_openid.userinfo(token)
            if kc_userinfo.get("sub") == user_id:
                user = user_service.get_or_create_user_from_keycloak(kc_userinfo)
            else:
                return jsonify({"error": "User not found"}), 404

        return jsonify({
            "id": user.id,
            "name": user.username,
            "email": user.email,
            "birthday": user.birthday.isoformat() if user.birthday else None,
            "faculty": user.faculty
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Tasks
@app.route("/api/tasks", methods=["GET"])
@keycloak_protect
def get_tasks():
    user_service = UserService(db.session, keycloak_admin)
    kc_user = user_service.get_or_create_user_from_keycloak(request.user)
    tasks = get_tasks_for_user(kc_user.id)
    return jsonify([task_to_dict(t) for t in tasks]), 200

@app.route("/api/tasks/user/<string:user_id>", methods=["GET"])
@keycloak_protect
def get_tasks_for_specific_user(user_id):
    tasks = get_tasks_for_user(user_id)
    return jsonify([task_to_dict(t) for t in tasks]), 200

# Groups
@app.route("/api/groups", methods=["GET"])
@keycloak_protect
def get_all_groups_endpoint():
    try:
        groups = get_all_groups()
        return jsonify([group_to_dict(g) for g in groups]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/groups/user/<string:user_id>", methods=["GET"])
@keycloak_protect
def get_groups_for_specific_user(user_id):
    try:
        user = db.session.get(User, user_id)
        user_service = UserService(db.session, keycloak_admin)
        if not user:
            auth_header = request.headers.get("Authorization")
            token = auth_header.split()[1]
            kc_userinfo = keycloak_openid.userinfo(token)
            if kc_userinfo.get("sub") == user_id:
                user = user_service.get_or_create_user_from_keycloak(kc_userinfo)
            else:
                return jsonify({"error": "User not found"}), 404

        groups = get_groups_for_user(user.id)
        groups_serialized = [group_to_dict(g, user.id) for g in groups]

        return jsonify(groups_serialized), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route("/api/groups/user/admin/<string:user_id>", methods=["GET"])
@keycloak_protect
def get_groups_for_specific_admin_user(user_id):
    try:
        user = db.session.get(User, user_id)
        user_service = UserService(db.session, keycloak_admin)
        if not user:
            auth_header = request.headers.get("Authorization")
            token = auth_header.split()[1]
            kc_userinfo = keycloak_openid.userinfo(token)
            if kc_userinfo.get("sub") == user_id:
                user = user_service.get_or_create_user_from_keycloak(kc_userinfo)
            else:
                return jsonify({"error": "User not found"}), 404

        # Fetch all groups the user belongs to
        all_groups = get_groups_for_user(user.id)

        # Only include groups where the user is admin
        admin_groups = []
        for g in all_groups:
            membership = next((m for m in g.group_memberships if m.user_id == user.id), None)
            if membership and membership.role == "admin":
                admin_groups.append(g)

        # Serialize
        groups_serialized = [group_to_dict(g, user.id) for g in admin_groups]

        return jsonify(groups_serialized), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/groups/<int:group_id>/members", methods=["GET"])
@keycloak_protect
def get_group_members(group_id):
    try:
        group = db.session.get(Group, group_id)
        if not group:
            return jsonify({"error": "Group not found"}), 404

        members = []
        for membership in group.group_memberships:
            user = membership.user
            if user:
                members.append({
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "role": membership.role
                })

        return jsonify({"members": members}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# -----------------------------
# PUT Routes
# -----------------------------
@app.route("/api/tasks/<int:task_id>", methods=["PUT"])
@keycloak_protect
def update_task(task_id):
    data = request.json
    user_service = UserService(db.session, keycloak_admin)
    kc_user = user_service.get_or_create_user_from_keycloak(request.user)
    try:
        updated_task = update_task_service(task_id, data, kc_user.id)
        return jsonify({"message": "Task updated", "task": task_to_dict(updated_task)}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/users/<string:user_id>", methods=["PUT"])
@keycloak_protect
def update_user(user_id):
    user_service = UserService(db.session, keycloak_admin)
    kc_user = user_service.get_or_create_user_from_keycloak(request.user)
    if kc_user.id != user_id:
        return jsonify({"error": "Cannot edit another user"}), 403

    data = request.json
    try:
        updated = user_service.update_user(user_id, data)
        return jsonify({
            "id": updated.id,
            "username": updated.username,
            "email": updated.email,
            "birthday": updated.birthday.isoformat() if updated.birthday else None,
            "faculty": updated.faculty
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# -----------------------------
# Run App
# -----------------------------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        # Uncomment to pre-populate all Keycloak users once
        populate_keycloak_users()
    app.run(host="0.0.0.0", port=5000, debug=True)
