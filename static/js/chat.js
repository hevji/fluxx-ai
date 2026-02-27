/**
 * chat.js — Drives the entire chat interface.
 *
 * Responsibilities:
 *  • Verify the user is logged in (via localStorage token); redirect if not.
 *  • Fetch and render the sidebar chat list.
 *  • Create / delete chats.
 *  • Load a chat's messages when selected.
 *  • Send messages and display assistant replies.
 *  • Keep the URL in sync with the active chat UUID (/c/<uuid>).
 */

// ─────────────────────────────────────────────
// Constants & state
// ─────────────────────────────────────────────
const API   = "";          // Flask runs on the same origin
let activeChatId = null;   // UUID of the currently open chat


// ─────────────────────────────────────────────
// Bootstrap on page load
// ─────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", async () => {
  // ── Auth guard ────────────────────────────────────────────────────────────
  // The server already renders a "not logged in" state; this JS guard handles
  // the case where the page was cached or the cookie expired.
  const token = localStorage.getItem("fb_id_token");
  if (!token) {
    // No token stored — show the overlay instead of redirecting abruptly
    showNotLoggedIn();
    return;
  }

  // Verify the token is still valid by calling the /me endpoint
  const me = await apiFetch("/api/auth/me");
  if (!me) {
    showNotLoggedIn();
    return;
  }

  // Show the logged-in user's email in the header
  document.getElementById("user-email").textContent = me.email || me.uid;

  // ── Wire up sidebar controls ──────────────────────────────────────────────
  document.getElementById("btn-new-chat").addEventListener("click", createNewChat);
  document.getElementById("btn-logout").addEventListener("click", logout);
  document.getElementById("send-btn").addEventListener("click", sendMessage);
  document.getElementById("msg-input").addEventListener("keydown", (e) => {
    // Send on Enter (but allow Shift+Enter for newlines)
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  // ── Load chat list ────────────────────────────────────────────────────────
  await loadChatList();

  // ── Open chat from URL if present (/c/<uuid>) ─────────────────────────────
  const pathParts = window.location.pathname.split("/").filter(Boolean);
  // pathname looks like ["c", "<uuid>"] or just ["c"]
  if (pathParts.length === 2 && pathParts[0] === "c") {
    await openChat(pathParts[1]);
  }
});


// ─────────────────────────────────────────────
// API helper
// ─────────────────────────────────────────────

/**
 * Thin wrapper around fetch() that:
 *  • Always sends the session cookie (credentials: "include").
 *  • Attaches the Firebase ID token as a fallback Authorization header.
 *  • Returns parsed JSON on success or null on failure.
 *
 * @param {string} path   — e.g. "/api/chats"
 * @param {object} opts   — standard fetch init options
 */
async function apiFetch(path, opts = {}) {
  const token = localStorage.getItem("fb_id_token");
  const headers = {
    "Content-Type": "application/json",
    ...(token ? { "Authorization": `Bearer ${token}` } : {}),
    ...(opts.headers || {}),
  };

  try {
    const res = await fetch(API + path, {
      ...opts,
      headers,
      credentials: "include", // send the HttpOnly session cookie
    });

    if (res.status === 401) {
      // Token expired — clean up and send to home
      localStorage.clear();
      window.location.href = "/";
      return null;
    }

    if (!res.ok) return null;
    return await res.json();
  } catch (err) {
    console.error("apiFetch error:", err);
    return null;
  }
}


// ─────────────────────────────────────────────
// Sidebar: chat list
// ─────────────────────────────────────────────

async function loadChatList() {
  const chats = await apiFetch("/api/chats");
  renderChatList(chats || []);
}

/**
 * Render the array of chat objects into the sidebar list.
 * @param {Array} chats
 */
function renderChatList(chats) {
  const list = document.getElementById("chat-list");
  list.innerHTML = "";

  if (chats.length === 0) {
    list.innerHTML = `<li class="empty-hint">No chats yet. Start one!</li>`;
    return;
  }

  chats.forEach((chat) => {
    const li = document.createElement("li");
    li.className = "chat-item" + (chat.id === activeChatId ? " active" : "");
    li.dataset.id = chat.id;

    li.innerHTML = `
      <span class="chat-title" title="${escapeHtml(chat.title)}">${escapeHtml(chat.title)}</span>
      <button class="delete-btn" title="Delete chat" data-id="${chat.id}">✕</button>
    `;

    // Click on title → open chat
    li.querySelector(".chat-title").addEventListener("click", () => openChat(chat.id));

    // Click on ✕ → delete chat
    li.querySelector(".delete-btn").addEventListener("click", (e) => {
      e.stopPropagation();
      deleteChat(chat.id);
    });

    list.appendChild(li);
  });
}


// ─────────────────────────────────────────────
// Create chat
// ─────────────────────────────────────────────

async function createNewChat() {
  const chat = await apiFetch("/api/chats", {
    method: "POST",
    body: JSON.stringify({ title: "New Chat" }),
  });

  if (!chat) return;

  await loadChatList();
  await openChat(chat.id);
}


// ─────────────────────────────────────────────
// Delete chat
// ─────────────────────────────────────────────

async function deleteChat(chatId) {
  if (!confirm("Delete this chat?")) return;

  const result = await apiFetch(`/api/chats/${chatId}`, { method: "DELETE" });
  if (result === null) return; // error already handled in apiFetch

  // If deleting the active chat, clear the main panel
  if (chatId === activeChatId) {
    activeChatId = null;
    clearMainPanel();
    history.pushState(null, "", "/c/");
  }

  await loadChatList();
}


// ─────────────────────────────────────────────
// Open / load chat
// ─────────────────────────────────────────────

/**
 * Load a chat by UUID: fetch its messages, render them, and update the URL.
 * @param {string} chatId — UUID
 */
async function openChat(chatId) {
  activeChatId = chatId;

  // Update the browser URL without a page reload
  history.pushState(null, "", `/c/${chatId}`);

  // Highlight active item in sidebar
  document.querySelectorAll(".chat-item").forEach((el) => {
    el.classList.toggle("active", el.dataset.id === chatId);
  });

  // Fetch the chat data
  const chat = await apiFetch(`/api/chats/${chatId}`);
  if (!chat) {
    showMainError("Could not load this chat.");
    return;
  }

  // Render the messages panel
  const panel = document.getElementById("messages-panel");
  panel.innerHTML = "";

  (chat.messages || []).forEach(({ role, content }) => {
    appendMessage(role, content);
  });

  // Show the input bar
  document.getElementById("chat-input-area").style.display = "flex";
  document.getElementById("msg-input").focus();
  scrollToBottom();
}

function clearMainPanel() {
  document.getElementById("messages-panel").innerHTML = `
    <div class="empty-chat">Select or create a chat to get started.</div>
  `;
  document.getElementById("chat-input-area").style.display = "none";
}


// ─────────────────────────────────────────────
// Messaging
// ─────────────────────────────────────────────

async function sendMessage() {
  if (!activeChatId) return;

  const input = document.getElementById("msg-input");
  const message = input.value.trim();
  if (!message) return;

  // Optimistically render the user's message
  appendMessage("user", message);
  input.value = "";
  scrollToBottom();

  // Show a typing indicator while waiting for the model
  const typingEl = appendTypingIndicator();

  // ── POST to the backend ───────────────────────────────────────────────────
  // The backend calls generate_reply() which currently returns placeholder text.
  // Replace generate_reply() in app.py to wire in Gemma 2B.
  const result = await apiFetch(`/api/chats/${activeChatId}/messages`, {
    method: "POST",
    body: JSON.stringify({ message }),
  });

  typingEl.remove();

  if (!result) {
    appendMessage("assistant", "⚠ Error: could not get a reply.");
  } else {
    appendMessage("assistant", result.assistant);

    // If this was the first message, the title may have changed — refresh list
    await loadChatList();

    // Re-highlight active item after list refresh
    document.querySelectorAll(".chat-item").forEach((el) => {
      el.classList.toggle("active", el.dataset.id === activeChatId);
    });
  }

  scrollToBottom();
}

/**
 * Create and append a message bubble to the messages panel.
 * @param {"user"|"assistant"} role
 * @param {string} content
 */
function appendMessage(role, content) {
  const panel = document.getElementById("messages-panel");
  const div   = document.createElement("div");
  div.className = `message ${role}`;
  div.innerHTML = `
    <div class="bubble">${escapeHtml(content)}</div>
  `;
  panel.appendChild(div);
  return div;
}

function appendTypingIndicator() {
  const panel = document.getElementById("messages-panel");
  const div   = document.createElement("div");
  div.className = "message assistant typing-wrap";
  div.innerHTML = `<div class="bubble typing"><span></span><span></span><span></span></div>`;
  panel.appendChild(div);
  return div;
}

function scrollToBottom() {
  const panel = document.getElementById("messages-panel");
  panel.scrollTop = panel.scrollHeight;
}


// ─────────────────────────────────────────────
// Logout
// ─────────────────────────────────────────────

async function logout() {
  // Sign out from Firebase on the client side
  if (typeof firebaseAuth !== "undefined") {
    await firebaseAuth.signOut().catch(() => {});
  }

  // Clear local storage
  localStorage.clear();

  // Tell the server to clear the session cookie
  await fetch("/api/auth/logout", { method: "POST", credentials: "include" });

  window.location.href = "/";
}


// ─────────────────────────────────────────────
// UI helpers
// ─────────────────────────────────────────────

function showNotLoggedIn() {
  document.getElementById("auth-overlay").style.display = "flex";
}

function showMainError(msg) {
  document.getElementById("messages-panel").innerHTML =
    `<div class="empty-chat error">${escapeHtml(msg)}</div>`;
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
