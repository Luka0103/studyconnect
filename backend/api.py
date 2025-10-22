from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from dotenv import load_dotenv
from keycloak import KeycloakError, KeycloakOpenID
from models import User
from services import (
    db, create_task_service, create_group_service,
    get_tasks_for_user, get_groups_for_user,
    join_group_service, update_task_service,
    get_or_create_user_from_keycloak, get_all_groups
)
from auth import keycloak_protect, keycloak_admin

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

def group_to_dict(g):
    members = [u.id for u in g.members] if g.members else []
    return {
        "id": g.id,
        "name": g.name,
        "description": g.description,
        "groupNumber": g.group_number,
        "inviteLink": g.invite_link,
        "members": members,
        "memberCount": len(members),
    }

# -----------------------------
# Populate all Keycloak users into local DB
# -----------------------------
def populate_keycloak_users():
    with app.app_context():
        try:
            keycloak_users = keycloak_openid.get_users()
            print(f"Found {len(keycloak_users)} Keycloak users.")
            created_count = 0
            for kc_user in keycloak_users:
                user_id = kc_user.get("id") or kc_user.get("sub")
                if not user_id:
                    continue
                existing_user = User.query.get(user_id)
                if not existing_user:
                    username = kc_user.get("username") or kc_user.get("email")
                    email = kc_user.get("email") or ""
                    user = User(id=user_id, username=username, email=email)
                    db.session.add(user)
                    created_count += 1
            db.session.commit()
            print(f"Created {created_count} new users in local DB.")
        except Exception as e:
            print(f"Error populating users: {e}")

# -----------------------------
# Authentication Route
# -----------------------------
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

# -----------------------------
# Protected Routes
# -----------------------------
@app.route("/api/users/<string:user_id>", methods=["GET"])
@keycloak_protect
def get_user(user_id):
    try:
        user = User.query.get(user_id)
        if not user:
            # Fetch Keycloak info dynamically
            auth_header = request.headers.get("Authorization")
            token = auth_header.split()[1]
            kc_userinfo = keycloak_openid.userinfo(token)
            if kc_userinfo.get("sub") == user_id:
                user = get_or_create_user_from_keycloak(kc_userinfo)
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

@app.route("/api/tasks/user/<string:user_id>", methods=["GET"])
@keycloak_protect
def get_tasks_for_specific_user(user_id):
    try:
        user = User.query.get(user_id)
        if not user:
            auth_header = request.headers.get("Authorization")
            token = auth_header.split()[1]
            kc_userinfo = keycloak_openid.userinfo(token)
            if kc_userinfo.get("sub") == user_id:
                user = get_or_create_user_from_keycloak(kc_userinfo)
            else:
                return jsonify({"error": "User not found"}), 404

        tasks = get_tasks_for_user(user.id)
        return jsonify([task_to_dict(t) for t in tasks]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/groups/user/<string:user_id>", methods=["GET"])
@keycloak_protect
def get_groups_for_specific_user(user_id):
    try:
        user = User.query.get(user_id)
        if not user:
            auth_header = request.headers.get("Authorization")
            token = auth_header.split()[1]
            kc_userinfo = keycloak_openid.userinfo(token)
            if kc_userinfo.get("sub") == user_id:
                user = get_or_create_user_from_keycloak(kc_userinfo)
            else:
                return jsonify({"error": "User not found"}), 404

        groups = get_groups_for_user(user.id)
        return jsonify([group_to_dict(g) for g in groups]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# -----------------------------
# Other Task & Group Routes
# -----------------------------
@app.route("/api/tasks", methods=["POST"])
@keycloak_protect
def create_task():
    data = request.json
    kc_user = get_or_create_user_from_keycloak(request.user)
    data["user_id"] = kc_user.id  # string
    try:
        task = create_task_service(data)
        return jsonify({"message": "Task created", "task": task_to_dict(task)}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/tasks", methods=["GET"])
@keycloak_protect
def get_tasks():
    kc_user = get_or_create_user_from_keycloak(request.user)
    tasks = get_tasks_for_user(kc_user.id)
    return jsonify([task_to_dict(t) for t in tasks]), 200

@app.route("/api/groups", methods=["POST"])
@keycloak_protect
def create_group():
    data = request.json
    try:
        group = create_group_service(data)
        return jsonify({"message": "Group created", "group": group_to_dict(group)}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    
@app.route("/api/groups", methods=["GET"])
@keycloak_protect
def get_all_groups_endpoint():
    """Return all groups for listing and joining."""
    try:
        groups = get_all_groups()
        return jsonify([group_to_dict(g) for g in groups]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/groups/join", methods=["POST"])
@keycloak_protect
def join_group():
    data = request.json
    kc_user = get_or_create_user_from_keycloak(request.user)
    group_id = data.get("group_id")

    try:
        group = join_group_service(kc_user.id, group_id)
        return jsonify({
            "message": f"User {kc_user.id} joined group {group.name}",
            "group": group_to_dict(group)
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/refresh", methods=["POST"])
def refresh_token():
    data = request.json
    refresh_token = data.get("refresh_token")

    if not refresh_token:
        return jsonify({"error": "Missing refresh token"}), 400

    try:
        # Get new tokens from Keycloak
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

@app.route("/api/tasks/<int:task_id>", methods=["PUT"])
@keycloak_protect
def update_task(task_id):
    """Update a specific task."""
    data = request.json
    try:
        # Call your existing service
        updated_task = update_task_service(task_id, data)
        return jsonify({
            "message": "Task updated",
            "task": task_to_dict(updated_task)
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    
@app.route("/api/users/register", methods=["POST"])
def register_user():
    data = request.json
    first_name = data.get("firstName")  # new
    last_name = data.get("lastName")    # new
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")
    birthday = data.get("birthday")
    faculty = data.get("faculty")

    if not first_name or not last_name or not username or not email or not password:
        return jsonify({"error": "firstName, lastName, username, email, and password are required"}), 400

    try:
        # 1️⃣ Create Keycloak user
        result = keycloak_admin.create_user({
            "username": username,
            "email": email,
            "firstName": first_name,   # added
            "lastName": last_name,     # added
            "enabled": True,
            "emailVerified": True,
            "attributes": {
                "faculty": faculty or "",
                "birthday": birthday or ""
            }
        })
        new_user_id = result if isinstance(result, str) else result.get("id")
        kc_user = keycloak_admin.get_user(new_user_id)

        # 2️⃣ Set password for the new user
        keycloak_admin.set_user_password(
            user_id=new_user_id,
            password=password,
            temporary=False
        )

        # 3️⃣ Remove required actions to allow immediate login
        keycloak_admin.update_user(
            user_id=new_user_id,
            payload={"requiredActions": []}
        )

        print("Required actions:", kc_user.get("requiredActions"))  # should be []

        # 4️⃣ Optional: Create user in local DB
        birthday_date = (
            datetime.strptime(birthday, "%Y-%m-%d").date() if birthday else None
        )
        user = User(
            id=new_user_id,
            username=username,
            email=email,
            birthday=birthday_date,
            faculty=faculty
        )
        db.session.add(user)
        db.session.commit()

        return jsonify({
            "message": "User registered successfully",
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "firstName": first_name,
            "lastName": last_name,
            "birthday": user.birthday.isoformat() if user.birthday else None,
            "faculty": user.faculty
        }), 201

    except KeycloakError as ke:
        return jsonify({
            "error": "Keycloak error",
            "status_code": ke.response_code,
            "response_body": (
                ke.response_body.decode() if isinstance(ke.response_body, bytes)
                else ke.response_body
            )
        }), ke.response_code

    except Exception as e:
        return jsonify({"error": "Internal server error", "details": str(e)}), 500


# -----------------------------
# Run App
# -----------------------------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        # Uncomment to pre-populate all Keycloak users once
        populate_keycloak_users()
    app.run(host="0.0.0.0", port=5000, debug=True)
