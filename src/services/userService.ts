import {
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  signOut,
  updateProfile as updateFirebaseProfile,
  onAuthStateChanged,
  type User as FirebaseUser,
} from 'firebase/auth'
import { auth, getIdToken, isFirebaseConfigured } from '../lib/firebase'
import type { UserProfile } from '../types'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'

export const userService = {
  /**
   * Registers a new user with Firebase Authentication and initializes their Firestore profile via FastAPI.
   */
  async register(email: string, pass: string, name?: string): Promise<UserProfile> {
    if (!auth || !isFirebaseConfigured) {
      throw new Error('Firebase Authentication is not configured in .env.local')
    }

    const userCredential = await createUserWithEmailAndPassword(auth, email, pass)
    if (name && userCredential.user) {
      await updateFirebaseProfile(userCredential.user, { displayName: name }).catch((err) =>
        console.warn('Failed to set Firebase displayName:', err)
      )
    }

    // Acquire fresh token and initialize minimal profile on FastAPI backend
    const token = await userCredential.user.getIdToken(true)
    const fallbackName = name || userCredential.user.displayName || email.split('@')[0]
    try {
      const res = await fetch(`${API_BASE_URL}/users/me`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          name: fallbackName,
          email: userCredential.user.email || email,
          profile_complete: false,
        }),
      })

      if (res.ok) {
        return (await res.json()) as UserProfile
      }
    } catch (err) {
      console.warn('Backend profile initialization deferred:', err)
    }

    // Clean minimal state if backend is temporarily unreachable; never use fictional defaults
    return {
      id: userCredential.user.uid,
      name: fallbackName,
      email: userCredential.user.email || email,
      profile_complete: false,
      streakDays: 0,
      totalWorkouts: 0,
      totalCaloriesBurned: 0,
      totalPoints: 0,
    }
  },

  /**
   * Signs in an existing user with email and password via Firebase Auth.
   */
  async login(email: string, pass: string): Promise<FirebaseUser> {
    if (!auth || !isFirebaseConfigured) {
      throw new Error('Firebase Authentication is not configured in .env.local')
    }
    const result = await signInWithEmailAndPassword(auth, email, pass)
    return result.user
  },

  /**
   * Signs out the current user from Firebase Auth.
   */
  async logout(): Promise<void> {
    if (auth) {
      await signOut(auth)
    }
  },

  /**
   * Subscribes to Firebase Auth state changes.
   */
  onAuthStateChange(callback: (user: FirebaseUser | null) => void): () => void {
    if (!auth) {
      callback(null)
      return () => {}
    }
    return onAuthStateChanged(auth, callback)
  },

  /**
   * Retrieves the current user profile from FastAPI /api/v1/users/me using the verified Firebase ID token.
   */
  async getUserProfile(): Promise<UserProfile> {
    const token = await getIdToken()

    if (token) {
      try {
        const res = await fetch(`${API_BASE_URL}/users/me`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        })

        if (res.ok) {
          return (await res.json()) as UserProfile
        }
        if (res.status === 401) {
          throw new Error('Unauthorized')
        }
      } catch (err) {
        console.warn('FastAPI /users/me call failed:', err)
        throw err
      }
    }

    throw new Error('No authentication token available')
  },

  /**
   * Updates current user profile on FastAPI backend using verified Firebase ID token.
   */
  async updateUserProfile(updates: Partial<UserProfile>): Promise<UserProfile> {
    const token = await getIdToken()

    if (!token) {
      throw new Error('Authentication required to update profile')
    }

    const res = await fetch(`${API_BASE_URL}/users/me`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(updates),
    })

    if (!res.ok) {
      const errorText = await res.text().catch(() => 'Update failed')
      throw new Error(`Profile update failed: ${errorText}`)
    }

    return (await res.json()) as UserProfile
  },
}
