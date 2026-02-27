"""
app.py — Flask backend for Gemma Chat
======================================
Handles authentication (Firebase), chat CRUD (Firestore), and
serving the frontend. All AI responses currently return placeholder text;
swap out the `generate_reply()` function at the bottom to wire up Gemma 2B.
"""

import os
import uuid
from functools import wraps

from flask import (
    Flask,
    request,
    jsonify,
    render_template,
    redirect,
    url_for,
    make_response,
)

# Firebase Admin SDK — handles server-side token verification and Firestore access
import firebase_admin
from firebase_admin import auth, credentials, firestore

# ─────────────────────────────────────────────
# App setup
# ─────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-in-prod")

# ─────────────────────────────────────────────
# Firebase initialisation
# ─────────────────────────────────────────────
# Place your serviceAccountKey.json in the project root.
# Download it from: Firebase Console → Project Settings → Service accounts → Generate new private key
SERVICE_ACCOUNT_PATH = os.path.join(os.path.dirname(__file__), "serviceAccountKey.json")

if not firebase_admin._apps:
    cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)
    firebase_admin.initialize_app(cred)

db = firestore.client()  # Firestore client — used for chat storage


# ─────────────────────────────────────────────
# Auth helpers
# ─────────────────────────────────────────────

def verify_id_token(id_token: str):
    """
    Verify a Firebase ID token (sent from the frontend after login).
    Returns the decoded token dict on success, or None on failure.
    """
    try:
        return auth.verify_id_token(id_token)
    except Exception:
        return None


def get_current_user():
    """
    Extract and verify the Firebase ID token stored in the `session_token` cookie.
    Returns the decoded token dict (containing uid, email, etc.) or None.
    """
    token = request.cookies.get("session_token")
    if not token:
        return None
    return verify_id_token(token)


def login_required(f):
    """
    Decorator: rejects API requests that don't carry a valid session token.
    Returns 401 JSON for API routes; page routes handle redirects themselves.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, user=user, **kwargs)
    return decorated


# ─────────────────────────────────────────────
# AI / Model helpers
# ─────────────────────────────────────────────

def generate_reply(user_message: str, chat_history: list) -> str:
    """
    ── REPLACE THIS FUNCTION TO PLUG IN GEMMA 2B ──────────────────────────────
    
    Currently returns a placeholder string.
    
    To use a locally-running Gemma 2B model (e.g. via llama.cpp, ctransformers,
    or the transformers library), load the model once at startup (outside this
    function) and call model.generate() / pipeline() here.

    Example with transformers:
    ─────────────────────────────────────────────
    from transformers import AutoTokenizer, AutoModelForCausalLM
    tokenizer = AutoTokenizer.from_pretrained("google/gemma-2b-it")
    model     = AutoModelForCausalLM.from_pretrained("google/gemma-2b-it")

    def generate_reply(user_message, chat_history):
        inputs = tokenizer(user_message, return_tensors="pt")
        outputs = model.generate(**inputs, max_new_tokens=200)
        return tokenizer.decode(outputs[0], skip_special_tokens=True)
    ─────────────────────────────────────────────
    """
    return "Gemma reply here"  # ← placeholder; replace with actual model call


# ─────────────────────────────────────────────
# Page routes
# ─────────────────────────────────────────────

@app.route("/")
def home():
    """Landing page — signup / login buttons."""
    return render_template("index.html")


@app.route("/c/", defaults={"chat_id": None})
@app.route("/c/<chat_id>")
def chat_page(chat_id):
    """
    Chat interface page.
    The frontend JS will check for a valid session token in localStorage and
    redirect to / if absent. The server also guards this route.
    """
    # We do a lightweight server-side check; the real auth guard is on the API.
    user = get_current_user()
    if not user:
        # Pass a flag so the template can show the "login required" message
        return render_template("chat.html", logged_in=False, chat_id=chat_id)
    return render_template("chat.html", logged_in=True, chat_id=chat_id)


# ─────────────────────────────────────────────
# Auth API endpoints
# ─────────────────────────────────────────────

@app.route("/api/auth/login", methods=["POST"])
def api_login():
    """
    Receives a Firebase ID token from the frontend (obtained after Firebase
    client-side sign-in), verifies it, and sets a session cookie.

    Request body (JSON):
        { "idToken": "<firebase-id-token>" }

    Response (JSON):
        { "uid": "...", "email": "..." }
    """
    data = request.get_json()
    id_token = data.get("idToken") if data else None

    if not id_token:
        return jsonify({"error": "Missing idToken"}), 400

    decoded = verify_id_token(id_token)
    if not decoded:
        return jsonify({"error": "Invalid token"}), 401

    # Set an HttpOnly cookie containing the raw ID token.
    # In production, use Firebase session cookies (auth.create_session_cookie)
    # for longer-lived, more secure sessions.
    response = make_response(jsonify({"uid": decoded["uid"], "email": decoded.get("email")}))
    response.set_cookie(
        "session_token",
        id_token,
        httponly=True,   # not accessible from JS (XSS protection)
        secure=False,    # set True in production (HTTPS)
        samesite="Lax",
        max_age=60 * 60 * 24,  # 1 day
    )
    return response


@app.route("/api/auth/logout", methods=["POST"])
def api_logout():
    """Clears the session cookie."""
    response = make_response(jsonify({"message": "Logged out"}))
    response.delete_cookie("session_token")
    return response


@app.route("/api/auth/signup", methods=["POST"])
def api_signup():
    """
    Signup is handled entirely client-side via the Firebase JS SDK.
    After signup the frontend obtains an ID token and calls /api/auth/login.
    This endpoint is a no-op placeholder for any future server-side signup logic.
    """
    return jsonify({"message": "Use Firebase client SDK for signup, then call /api/auth/login"}), 200


@app.route("/api/auth/me", methods=["GET"])
@login_required
def api_me(user):
    """Returns the currently authenticated user's info."""
    return jsonify({"uid": user["uid"], "email": user.get("email")})


# ─────────────────────────────────────────────
# Chat API endpoints
# ─────────────────────────────────────────────

@app.route("/api/chats", methods=["GET"])
@login_required
def api_get_chats(user):
    """
    Fetch all chats belonging to the logged-in user, ordered by creation time.

    Response (JSON):
        [ { "id": "<uuid>", "title": "...", "created_at": "..." }, ... ]
    """
    uid = user["uid"]
    chats_ref = (
        db.collection("chats")
        .where("uid", "==", uid)
        .order_by("created_at", direction=firestore.Query.DESCENDING)
    )
    docs = chats_ref.stream()
    chats = []
    for doc in docs:
        data = doc.to_dict()
        chats.append({
            "id": doc.id,
            "title": data.get("title", "Untitled Chat"),
            "created_at": data.get("created_at").isoformat() if data.get("created_at") else None,
        })
    return jsonify(chats)


@app.route("/api/chats", methods=["POST"])
@login_required
def api_create_chat(user):
    """
    Create a new chat document in Firestore with a fresh UUID.

    Request body (JSON, optional):
        { "title": "My new chat" }

    Response (JSON):
        { "id": "<uuid>", "title": "...", "created_at": "..." }
    """
    uid = user["uid"]
    data = request.get_json() or {}
    chat_id = str(uuid.uuid4())  # Unique identifier for this chat
    title = data.get("title", "New Chat")

    chat_doc = {
        "uid": uid,
        "title": title,
        "created_at": firestore.SERVER_TIMESTAMP,
        "messages": [],  # Messages are stored as a subcollection or inline list
    }

    db.collection("chats").document(chat_id).set(chat_doc)

    return jsonify({"id": chat_id, "title": title}), 201


@app.route("/api/chats/<chat_id>", methods=["GET"])
@login_required
def api_get_chat(user, chat_id):
    """
    Fetch a specific chat (including its messages) by UUID.
    Only the owning user can access their chats.
    """
    uid = user["uid"]
    doc = db.collection("chats").document(chat_id).get()

    if not doc.exists:
        return jsonify({"error": "Chat not found"}), 404

    data = doc.to_dict()
    if data.get("uid") != uid:
        return jsonify({"error": "Forbidden"}), 403

    return jsonify({
        "id": doc.id,
        "title": data.get("title", "Untitled"),
        "messages": data.get("messages", []),
        "created_at": data.get("created_at").isoformat() if data.get("created_at") else None,
    })


@app.route("/api/chats/<chat_id>", methods=["DELETE"])
@login_required
def api_delete_chat(user, chat_id):
    """Delete a chat document. Only the owner can delete."""
    uid = user["uid"]
    doc_ref = db.collection("chats").document(chat_id)
    doc = doc_ref.get()

    if not doc.exists:
        return jsonify({"error": "Chat not found"}), 404
    if doc.to_dict().get("uid") != uid:
        return jsonify({"error": "Forbidden"}), 403

    doc_ref.delete()
    return jsonify({"message": "Deleted"}), 200


@app.route("/api/chats/<chat_id>/messages", methods=["POST"])
@login_required
def api_send_message(user, chat_id):
    """
    Append a user message to a chat and get a model reply.

    Request body (JSON):
        { "message": "Hello, Gemma!" }

    Response (JSON):
        { "user": "Hello, Gemma!", "assistant": "Gemma reply here" }

    ── TO CONNECT GEMMA 2B ─────────────────────────────────────────────────────
    Edit `generate_reply()` above. The full chat history is passed so you can
    implement multi-turn conversation context.
    ─────────────────────────────────────────────────────────────────────────────
    """
    uid = user["uid"]
    doc_ref = db.collection("chats").document(chat_id)
    doc = doc_ref.get()

    if not doc.exists:
        return jsonify({"error": "Chat not found"}), 404
    if doc.to_dict().get("uid") != uid:
        return jsonify({"error": "Forbidden"}), 403

    data = request.get_json() or {}
    user_message = data.get("message", "").strip()
    if not user_message:
        return jsonify({"error": "Empty message"}), 400

    chat_data = doc.to_dict()
    history = chat_data.get("messages", [])

    # Generate AI reply (placeholder — see generate_reply() above)
    assistant_reply = generate_reply(user_message, history)

    # Build new message entries
    user_entry = {"role": "user", "content": user_message}
    assistant_entry = {"role": "assistant", "content": assistant_reply}

    # Persist messages to Firestore
    doc_ref.update({
        "messages": firestore.ArrayUnion([user_entry, assistant_entry])
    })

    # Auto-update chat title from first user message
    if not history:
        short_title = user_message[:40] + ("…" if len(user_message) > 40 else "")
        doc_ref.update({"title": short_title})

    return jsonify({"user": user_message, "assistant": assistant_reply})


# ─────────────────────────────────────────────
# Run
# ─────────────────────────────────────────────
if __name__ == "__main__":
    app.run(host="localhost", port=5000, debug=True)