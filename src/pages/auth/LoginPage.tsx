import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { sendPasswordResetEmail } from 'firebase/auth'
import { auth, isFirebaseConfigured } from '../../lib/firebase'
import { useUser } from '../../hooks'
import { userService } from '../../services'
import { Card, Input, Button } from '../../components/ui'

function getFriendlyAuthError(err: unknown): string {
  if (!err || typeof err !== 'object') return 'An unexpected error occurred. Please try again.'
  const code = 'code' in err ? String((err as { code: unknown }).code) : ''
  switch (code) {
    case 'auth/invalid-credential':
    case 'auth/wrong-password':
    case 'auth/user-not-found':
      return 'Invalid email or password. Please verify your credentials.'
    case 'auth/email-already-in-use':
      return 'This email address is already registered. Please sign in.'
    case 'auth/weak-password':
      return 'Password should be at least 6 characters.'
    case 'auth/invalid-email':
      return 'Please enter a valid email address.'
    case 'auth/network-request-failed':
      return 'Network error. Please check your internet connection.'
    case 'auth/too-many-requests':
      return 'Too many attempts. Please try again in a few moments.'
    default:
      return 'message' in err ? String((err as { message: unknown }).message) : 'Authentication failed.'
  }
}

export const LoginPage: React.FC = () => {
  const navigate = useNavigate()
  const { login } = useUser()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    if (!email.trim() || !password) {
      setError('Please enter both email and password.')
      return
    }

    if (!isFirebaseConfigured) {
      setError('Firebase Authentication is not configured. Check .env.local configuration.')
      return
    }

    setLoading(true)
    try {
      await login(email.trim(), password)
      try {
        const profile = await userService.getUserProfile()
        if (profile && profile.profile_complete === false) {
          navigate('/onboarding')
        } else {
          navigate('/dashboard')
        }
      } catch {
        navigate('/dashboard')
      }
    } catch (err) {
      console.error('Login error:', err)
      setError(getFriendlyAuthError(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
      <Card className="w-full max-w-md p-6 space-y-4">
        <h1 className="text-xl font-bold text-slate-100 text-center">Log In to AI FITNESS</h1>
        <p className="text-xs text-slate-400 text-center">Your AI Fitness Coach</p>

        {error && (
          <div className="rounded-xl border border-red-500/40 bg-red-950/30 p-3 text-xs text-red-400 text-center">
            {error}
          </div>
        )}

        <form onSubmit={handleLogin} className="space-y-4">
          <Input
            label="Email"
            type="email"
            placeholder="your.email@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoComplete="email"
          />
          <Input
            label="Password"
            type="password"
            placeholder="••••••••"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            autoComplete="current-password"
          />
          <div className="flex justify-end">
            <Link to="/forgot-password" className="text-xs text-slate-400 hover:text-emerald-400">
              Forgot password?
            </Link>
          </div>
          <Button type="submit" className="w-full" isLoading={loading}>
            Sign In
          </Button>
        </form>

        <div className="text-center text-xs text-slate-400 pt-2">
          Don't have an account?{' '}
          <Link to="/signup" className="text-emerald-400 underline">
            Sign Up
          </Link>
        </div>
      </Card>
    </div>
  )
}

export const SignupPage: React.FC = () => {
  const navigate = useNavigate()
  const { register } = useUser()
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    if (!email.trim() || !password) {
      setError('Please provide an email and password.')
      return
    }

    if (password.length < 6) {
      setError('Password must be at least 6 characters long.')
      return
    }

    if (!isFirebaseConfigured) {
      setError('Firebase Authentication is not configured. Check .env.local configuration.')
      return
    }

    setLoading(true)
    try {
      await register(email.trim(), password, name.trim() || undefined)
      navigate('/onboarding')
    } catch (err) {
      console.error('Signup error:', err)
      setError(getFriendlyAuthError(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
      <Card className="w-full max-w-md p-6 space-y-4">
        <h1 className="text-xl font-bold text-slate-100 text-center">Create Your Account</h1>

        {error && (
          <div className="rounded-xl border border-red-500/40 bg-red-950/30 p-3 text-xs text-red-400 text-center">
            {error}
          </div>
        )}

        <form onSubmit={handleSignup} className="space-y-4">
          <Input
            label="Full Name"
            placeholder="e.g. Alex Morgan"
            value={name}
            onChange={(e) => setName(e.target.value)}
            autoComplete="name"
          />
          <Input
            label="Email"
            type="email"
            placeholder="your.email@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoComplete="email"
          />
          <Input
            label="Password"
            type="password"
            placeholder="••••••••"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            autoComplete="new-password"
          />
          <Button type="submit" className="w-full" isLoading={loading}>
            Create Account
          </Button>
        </form>

        <div className="text-center text-xs text-slate-400 pt-2">
          Already have an account?{' '}
          <Link to="/login" className="text-emerald-400 underline">
            Sign In
          </Link>
        </div>
      </Card>
    </div>
  )
}

export const ForgotPasswordPage: React.FC = () => {
  const [email, setEmail] = useState('')
  const [statusMsg, setStatusMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  const [loading, setLoading] = useState(false)

  const handleReset = async (e: React.FormEvent) => {
    e.preventDefault()
    setStatusMsg(null)

    if (!email.trim()) {
      setStatusMsg({ type: 'error', text: 'Please enter your email address.' })
      return
    }

    if (!auth || !isFirebaseConfigured) {
      setStatusMsg({ type: 'error', text: 'Firebase is not configured in .env.local.' })
      return
    }

    setLoading(true)
    try {
      await sendPasswordResetEmail(auth, email.trim())
      setStatusMsg({
        type: 'success',
        text: 'Password reset link sent! Please check your inbox.',
      })
    } catch (err) {
      console.error('Password reset error:', err)
      setStatusMsg({ type: 'error', text: getFriendlyAuthError(err) })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
      <Card className="w-full max-w-md p-6 text-center space-y-3">
        <h1 className="text-xl font-bold text-slate-100">Reset Password</h1>
        <p className="text-xs text-slate-400">Enter your email to receive a password reset link.</p>

        {statusMsg && (
          <div
            className={`rounded-xl border p-3 text-xs text-center ${
              statusMsg.type === 'success'
                ? 'border-emerald-500/40 bg-emerald-950/30 text-emerald-400'
                : 'border-red-500/40 bg-red-950/30 text-red-400'
            }`}
          >
            {statusMsg.text}
          </div>
        )}

        <form onSubmit={handleReset} className="space-y-4 text-left">
          <Input
            label="Email"
            type="email"
            placeholder="your.email@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoComplete="email"
          />
          <Button type="submit" className="w-full" isLoading={loading}>
            Send Reset Link
          </Button>
        </form>

        <div className="text-center text-xs text-slate-400 pt-2">
          Remember your password?{' '}
          <Link to="/login" className="text-emerald-400 underline">
            Back to Sign In
          </Link>
        </div>
      </Card>
    </div>
  )
}
