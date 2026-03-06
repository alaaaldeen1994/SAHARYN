// Firebase Initialization for Saharyn AI
import { initializeApp } from "https://www.gstatic.com/firebasejs/10.8.0/firebase-app.js";
import { getAuth, onAuthStateChanged, signInWithPopup, GoogleAuthProvider, signOut } from "https://www.gstatic.com/firebasejs/10.8.0/firebase-auth.js";
import firebaseConfig from "./firebase-config.js";

// Initialize Firebase
let app, auth, provider;
try {
    if (firebaseConfig.apiKey && firebaseConfig.apiKey !== "YOUR_API_KEY") {
        app = initializeApp(firebaseConfig);
        auth = getAuth(app);
        provider = new GoogleAuthProvider();
    } else {
        console.warn("Firebase Not Configured: Using local guest mode. Please update firebase-config.js.");
    }
} catch (e) {
    console.error("Firebase Init Failed:", e);
}

// Check authentication state
if (auth) {
    onAuthStateChanged(auth, (user) => {
        if (user) {
            console.log("Authenticated as:", user.email);
            window.dispatchEvent(new CustomEvent('saharyn-auth-changed', { detail: user }));
        } else {
            console.log("No user authenticated.");
        }
    });
}

// Helper for Google Sign-In
export async function login() {
    if (!auth) {
        alert("Firebase is not configured. Please add your credentials in firebase-config.js first.");
        return null;
    }
    try {
        const result = await signInWithPopup(auth, provider);
        return result.user;
    } catch (error) {
        console.error("Auth error:", error);
    }
}

// Helper for Logout
export async function logout() {
    if (!auth) return;
    await signOut(auth);
    window.location.href = 'index.html';
}

export { auth };
