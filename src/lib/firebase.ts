import { initializeApp, getApps, getApp, type FirebaseApp } from 'firebase/app'
import {
  getAuth,
  browserLocalPersistence,
  setPersistence,
  type Auth,
} from 'firebase/auth'

const env = (typeof import.meta !== 'undefined' && (import.meta as any).env) ? (import.meta as any).env : {}
const firebaseConfig = {
  apiKey: env.VITE_FIREBASE_API_KEY,
  authDomain: env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: env.VITE_FIREBASE_PROJECT_ID,
  storageBucket: env.VITE_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: env.VITE_FIREBASE_MESSAGING_SENDER_ID,
  appId: env.VITE_FIREBASE_APP_ID,
}

export const isFirebaseConfigured: boolean = Boolean(
  firebaseConfig.apiKey &&
  firebaseConfig.authDomain &&
  firebaseConfig.projectId &&
  firebaseConfig.appId
)

export const app: FirebaseApp | null = isFirebaseConfigured
  ? (getApps().length === 0 ? initializeApp(firebaseConfig) : getApp())
  : null

export const auth: Auth | null = app ? getAuth(app) : null

// Ensure local persistence is active
if (auth) {
  setPersistence(auth, browserLocalPersistence).catch((err) => {
    console.warn('Failed to set Firebase auth persistence:', err)
  })
}

/**
 * Returns the active user's Firebase ID token for authenticating against FastAPI backend.
 */
export async function getIdToken(forceRefresh = false): Promise<string | null> {
  if (!auth?.currentUser) {
    return null
  }
  try {
    return await auth.currentUser.getIdToken(forceRefresh)
  } catch (err) {
    console.error('Error fetching Firebase ID token:', err)
    return null
  }
}
