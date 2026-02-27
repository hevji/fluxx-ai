"""
app.py — Gemma Chat backend (no auth, no Firebase)
====================================================
Endpoints:
  GET  /                        → landing page
  GET  /c/                      → chat interface (no uuid)
  GET  /c/<uuid>                → chat interface with specific chat
  GET  /api/chats               → list all chats (stored in memory / JSON file)
  POST /api/chats               → create new chat, returns {id, title}
  GET  /api/chats/<id>          → fetch chat + messages
  DELETE /api/chats/<id>        → delete a chat
  POST /api/chats/<id>/messages → send a message, get AI reply

Chat data is persisted to chats.json on disk so it survives server restarts.

TO CONNECT GEMMA 2B:
  Edit generate_reply() below. Load your model once at startup,
  call it inside that function, and return the string response.
"""

import json
import os
import uuid
from datetime import datetime

from flask import Flask, jsonify, render_template, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # allow the frontend (even if served separately) to call the API

# ─────────────────────────────────────────────
# Simple file-based storage
# ─────────────────────────────────────────────
DATA_FILE = os.path.join(os.path.dirname(__file__), "chats.json")


def load_chats() -> dict:
    """Load chat data from disk. Returns a dict keyed by chat UUID."""
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r") as f:
        return json.load(f)


def save_chats(chats: dict):
    """Persist chat data to disk."""
    with open(DATA_FILE, "w") as f:
        json.dump(chats, f, indent=2)


# ─────────────────────────────────────────────
# AI / Model — replace this to use Gemma 2B
# ─────────────────────────────────────────────

# ── LOAD YOUR MODEL HERE (once at startup) ──────────────────────────────────
# Example (transformers):
#   from transformers import AutoTokenizer, AutoModelForCausalLM
#   import torch
#   _tokenizer = AutoTokenizer.from_pretrained("google/gemma-2b-it")
#   _model     = AutoModelForCausalLM.from_pretrained(
#                    "google/gemma-2b-it", torch_dtype=torch.float16, device_map="auto")
#
# Example (llama-cpp-python with a GGUF file):
#   from llama_cpp import Llama
#   _llm = Llama(model_path="./models/gemma-2b-it.gguf", n_ctx=2048)
# ─────────────────────────────────────────────────────────────────────────────

def generate_reply(user_message: str, history: list) -> str:
    """
    ── REPLACE THIS FUNCTION TO USE GEMMA 2B ───────────────────────────────────
    `history` is a list of {"role": "user"|"assistant", "content": "..."} dicts.

    transformers example:
        prompt = build_prompt(history, user_message)   # build your template
        inputs  = _tokenizer(prompt, return_tensors="pt").to(_model.device)
        outputs = _model.generate(**inputs, max_new_tokens=256)
        return _tokenizer.decode(outputs[0], skip_special_tokens=True)

    llama-cpp example:
        prompt = f"<start_of_turn>user\n{user_message}<end_of_turn>\n<start_of_turn>model\n"
        out = _llm(prompt, max_tokens=256, stop=["<end_of_turn>"])
        return out["choices"][0]["text"].strip()
    ─────────────────────────────────────────────────────────────────────────────
    """
    return "Gemma reply here"   # ← placeholder


# ─────────────────────────────────────────────
# Page routes
# ─────────────────────────────────────────────

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/c/", defaults={"chat_id": None})
@app.route("/c/<chat_id>")
def chat_page(chat_id):
    return render_template("chat.html")


# ─────────────────────────────────────────────
# Chat API
# ─────────────────────────────────────────────

@app.route("/api/chats", methods=["GET"])
def api_list_chats():
    """Return all chats sorted newest-first."""
    chats = load_chats()
    result = [
        {"id": k, "title": v["title"], "created_at": v["created_at"]}
        for k, v in chats.items()
    ]
    result.sort(key=lambda x: x["created_at"], reverse=True)
    return jsonify(result)


@app.route("/api/chats", methods=["POST"])
def api_create_chat():
    """Create a new chat and return it."""
    chats = load_chats()
    chat_id = str(uuid.uuid4())
    chats[chat_id] = {
        "title": "New Chat",
        "created_at": datetime.utcnow().isoformat(),
        "messages": [],
    }
    save_chats(chats)
    return jsonify({"id": chat_id, "title": "New Chat"}), 201


@app.route("/api/chats/<chat_id>", methods=["GET"])
def api_get_chat(chat_id):
    chats = load_chats()
    chat = chats.get(chat_id)
    if not chat:
        return jsonify({"error": "Not found"}), 404
    return jsonify({"id": chat_id, **chat})


@app.route("/api/chats/<chat_id>", methods=["DELETE"])
def api_delete_chat(chat_id):
    chats = load_chats()
    if chat_id not in chats:
        return jsonify({"error": "Not found"}), 404
    del chats[chat_id]
    save_chats(chats)
    return jsonify({"message": "Deleted"})


@app.route("/api/chats/<chat_id>/messages", methods=["POST"])
def api_send_message(chat_id):
    """
    Append a user message, call the model, append assistant reply, persist.
    Body: { "message": "..." }
    """
    chats = load_chats()
    chat = chats.get(chat_id)
    if not chat:
        return jsonify({"error": "Not found"}), 404

    data = request.get_json() or {}
    user_message = data.get("message", "").strip()
    if not user_message:
        return jsonify({"error": "Empty message"}), 400

    history = chat.get("messages", [])

    # ── Get reply from model (swap generate_reply() for real Gemma) ───────────
    reply = generate_reply(user_message, history)

    # Append both turns
    history.append({"role": "user",      "content": user_message})
    history.append({"role": "assistant", "content": reply})
    chat["messages"] = history

    # Auto-title the chat from the first user message
    if len(history) == 2:
        chat["title"] = user_message[:45] + ("…" if len(user_message) > 45 else "")

    chats[chat_id] = chat
    save_chats(chats)

    return jsonify({"user": user_message, "assistant": reply})


# ─────────────────────────────────────────────
if __name__ == "__main__":
    app.run(host="localhost", port=5000, debug=True)
