/**
 * auth.js — Handles signup and login on the landing page.
 *
 * Flow:
 *  1. User enters email + password and clicks Sign Up or Log In.
 *  2. Firebase client SDK creates / authenticates the user.
 *  3. We retrieve the Firebase ID token.
 *  4. We POST the ID token to /api/auth/login so Flask can set a session cookie.
 *  5. We also store the token in localStorage so the chat page can use it for
 *     subsequent API calls before the cookie is validated.
 *  6. Redirect to /c/.
 */

// ─────────────────────────────────────────────
// DOM references (set after DOMContentLoaded)
// ─────────────────────────────────────────────
let emailInput, passwordInput, authError;

document.addEventListener("DOMContentLoaded", () => {
  emailInput    = document.getElementById("auth-email");
  passwordInput = document.getElementById("auth-password");
  authError     = document.getElementById("auth-error");

  document.getElementById("btn-signup").addEventListener("click", handleSignup);
  document.getElementById("btn-login").addEventListener("click", handleLogin);

  // If already logged in, skip to chat
  firebaseAuth.onAuthStateChanged(async (user) => {
    if (user) {
      await exchangeTokenAndRedirect(user);
    }
  });
});


// ─────────────────────────────────────────────
// Signup
// ─────────────────────────────────────────────
async function handleSignup() {
  const email    = emailInput.value.trim();
  const password = passwordInput.value;
  clearError();

  if (!email || !password) {
    showError("Please enter both email and password.");
    return;
  }

  try {
    // Create a new Firebase user with email + password
    const cred = await firebaseAuth.createUserWithEmailAndPassword(email, password);
    await exchangeTokenAndRedirect(cred.user);
  } catch (err) {
    showError(err.message);
  }
}


// ─────────────────────────────────────────────
// Login
// ─────────────────────────────────────────────
async function handleLogin() {
  const email    = emailInput.value.trim();
  const password = passwordInput.value;
  clearError();

  if (!email || !password) {
    showError("Please enter both email and password.");
    return;
  }

  try {
    // Sign in an existing Firebase user
    const cred = await firebaseAuth.signInWithEmailAndPassword(email, password);
    await exchangeTokenAndRedirect(cred.user);
  } catch (err) {
    showError(err.message);
  }
}


// ─────────────────────────────────────────────
// Token exchange + redirect
// ─────────────────────────────────────────────

/**
 * After a successful Firebase auth operation:
 *  1. Get the ID token (JWT) from Firebase.
 *  2. POST it to the Flask backend to set a session cookie.
 *  3. Store it in localStorage as a fallback for client-side guards.
 *  4. Redirect to the chat page.
 *
 * @param {firebase.User} user
 */
async function exchangeTokenAndRedirect(user) {
  try {
    // Force-refresh = false; use cached token if not expired
    const idToken = await user.getIdToken(/* forceRefresh= */ false);

    // Store in localStorage so the chat JS can read it immediately
    localStorage.setItem("fb_id_token", idToken);
    localStorage.setItem("fb_uid", user.uid);
    localStorage.setItem("fb_email", user.email || "");

    // Send to Flask to create the session cookie
    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ idToken }),
      credentials: "include", // needed to receive the Set-Cookie header
    });

    if (!res.ok) {
      const body = await res.json();
      showError(body.error || "Login failed.");
      return;
    }

    // Navigate to the chat interface
    window.location.href = "/c/";
  } catch (err) {
    showError("Token exchange failed: " + err.message);
  }
}


// ─────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────
function showError(msg) {
  authError.textContent = msg;
  authError.style.display = "block";
}

function clearError() {
  authError.textContent = "";
  authError.style.display = "none";
}
