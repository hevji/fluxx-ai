/**
 * firebase-config.js
 * ══════════════════════════════════════════════════════
 * Replace the placeholder values below with the real credentials
 * from your Firebase project.
 *
 * How to find them:
 *   Firebase Console → Your Project → Project Settings (⚙) →
 *   General tab → "Your apps" section → Web app config object
 *
 * NEVER commit real credentials to a public repository.
 * Use environment variables or a secrets manager in production.
 * ══════════════════════════════════════════════════════
 */

const firebaseConfig = {
  apiKey:            "YOUR_API_KEY",
  authDomain:        "YOUR_PROJECT_ID.firebaseapp.com",
  projectId:         "YOUR_PROJECT_ID",
  storageBucket:     "YOUR_PROJECT_ID.appspot.com",
  messagingSenderId: "YOUR_MESSAGING_SENDER_ID",
  appId:             "YOUR_APP_ID",
};

// Initialise Firebase (only once)
if (!firebase.apps || !firebase.apps.length) {
  firebase.initializeApp(firebaseConfig);
}

const firebaseAuth = firebase.auth(); // export for use in other scripts
