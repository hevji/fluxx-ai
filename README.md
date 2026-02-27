# Gemma Chat

No auth. No Firebase. No cloud. Just Flask + a local model.

## Structure

```
gemma-chat/
├── app.py            ← Flask backend
├── requirements.txt
├── chats.json        ← auto-created on first run (your chat history)
└── templates/
    ├── index.html    ← landing page ("Go to Chat" button)
    └── chat.html     ← chat interface with sidebar + messages
```

## Run

```bash
pip install -r requirements.txt
python app.py
```

Open http://localhost:5000

## Connect Gemma 2B

Edit `generate_reply()` in `app.py`. Two ready-to-use examples are in the comments:

**transformers:**
```python
from transformers import AutoTokenizer, AutoModelForCausalLM
_tok = AutoTokenizer.from_pretrained("google/gemma-2b-it")
_mdl = AutoModelForCausalLM.from_pretrained("google/gemma-2b-it", device_map="auto")

def generate_reply(user_message, history):
    prompt = f"<start_of_turn>user\n{user_message}<end_of_turn>\n<start_of_turn>model\n"
    ids = _tok(prompt, return_tensors="pt").to(_mdl.device)
    out = _mdl.generate(**ids, max_new_tokens=256)
    return _tok.decode(out[0][ids.input_ids.shape[-1]:], skip_special_tokens=True).strip()
```

**llama-cpp-python (GGUF):**
```python
from llama_cpp import Llama
_llm = Llama(model_path="./models/gemma-2b-it.gguf", n_ctx=2048)

def generate_reply(user_message, history):
    prompt = f"<start_of_turn>user\n{user_message}<end_of_turn>\n<start_of_turn>model\n"
    out = _llm(prompt, max_tokens=256, stop=["<end_of_turn>"])
    return out["choices"][0]["text"].strip()
```
