# Gemma Chat 🔮

A production-ready chat skeleton connecting a Flask backend to Firebase Auth + Firestore,
with a clean dark UI ready for Gemma 2B (local model).

---

## Project structure

```
gemma-chat/
├── app.py                        ← Flask backend (auth, chat CRUD, AI stub)
├── requirements.txt
├── serviceAccountKey.json        ← YOU create this (see step 2)
├── static/
│   ├── css/style.css
│   └── js/
│       ├── firebase-config.js   ← YOU fill in your Firebase web credentials
│       ├── auth.js              ← signup / login flow
│       └── chat.js              ← chat UI logic
└── templates/
    ├── index.html               ← landing page
    └── chat.html                ← chat interface (/c/<uuid>)
```

---

## Quick start

### 1. Create a Firebase project

1. Go to https://console.firebase.google.com and create a project.
2. Enable **Authentication** → Sign-in method → **Email/Password**.
3. Enable **Firestore Database** (start in production mode, add rules as needed).

### 2. Get backend credentials (service account)

Firebase Console → Project Settings (⚙) → **Service accounts** → **Generate new private key**.

Save the downloaded file as `serviceAccountKey.json` in the project root.

⚠️  Never commit this file to a public repository.

### 3. Get frontend credentials (web app config)

Firebase Console → Project Settings → **General** → scroll to "Your apps" → **Add app** (Web icon `</>`).

Copy the config object and paste it into `static/js/firebase-config.js`, replacing the placeholder values.

### 4. Install Python dependencies

```bash
python3 -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 5. Run the server

```bash
python app.py
```

Open http://localhost:5000 in your browser.

---

## Connecting Gemma 2B (local model)

All AI responses are currently stubs. To wire in your local Gemma 2B model,
edit the `generate_reply()` function in `app.py`.

**Example with HuggingFace Transformers:**

```python
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

# Load once at startup (outside the function)
MODEL_NAME = "google/gemma-2b-it"
tokenizer  = AutoTokenizer.from_pretrained(MODEL_NAME)
model      = AutoModelForCausalLM.from_pretrained(MODEL_NAME, torch_dtype=torch.float16, device_map="auto")

def generate_reply(user_message: str, chat_history: list) -> str:
    # Build a simple prompt from history
    prompt = ""
    for msg in chat_history[-10:]:  # last 10 messages for context
        role   = "User" if msg["role"] == "user" else "Model"
        prompt += f"{role}: {msg['content']}\n"
    prompt += f"User: {user_message}\nModel:"

    inputs  = tokenizer(prompt, return_tensors="pt").to(model.device)
    outputs = model.generate(**inputs, max_new_tokens=256, do_sample=True, temperature=0.7)
    reply   = tokenizer.decode(outputs[0][inputs["input_ids"].shape[-1]:], skip_special_tokens=True)
    return reply.strip()
```

**Example with llama.cpp (llama-cpp-python):**

```python
from llama_cpp import Llama

llm = Llama(model_path="./models/gemma-2b-it.gguf", n_ctx=2048)

def generate_reply(user_message: str, chat_history: list) -> str:
    prompt = f"<start_of_turn>user\n{user_message}<end_of_turn>\n<start_of_turn>model\n"
    output = llm(prompt, max_tokens=256, stop=["<end_of_turn>"])
    return output["choices"][0]["text"].strip()
```

---

## Firestore data model

```
chats (collection)
  └── <uuid> (document)
        uid:        "firebase-user-uid"
        title:      "First message preview…"
        created_at: Timestamp
        messages:   [
          { role: "user",      content: "Hello!" },
          { role: "assistant", content: "Gemma reply here" },
          ...
        ]
```

---

## Firestore security rules (recommended)

```
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /chats/{chatId} {
      allow read, write: if request.auth != null && request.auth.uid == resource.data.uid;
      allow create:      if request.auth != null && request.resource.data.uid == request.auth.uid;
    }
  }
}
```
