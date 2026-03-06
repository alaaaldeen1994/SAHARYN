// Firebase Initialization for Saharyn AI - Tech Uplink Verified
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

// Helper for Account Deletion
export async function deleteAccount() {
    if (!auth || !auth.currentUser) return;
    const user = auth.currentUser;
    if (confirm("CRITICAL: This will permanently delete your SAHARYN AI account and all associated institutional data. This action cannot be undone. Proceed?")) {
        try {
            await user.delete();
            window.location.href = 'index.html';
        } catch (error) {
            console.error("Account deletion failed:", error);
            if (error.code === 'auth/requires-recent-login') {
                alert("For security, please sign out and sign back in before deleting your account.");
            } else {
                alert("Deletion failed: " + error.message);
            }
        }
    }
}

export { auth };
