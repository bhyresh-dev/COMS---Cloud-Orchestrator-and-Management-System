import { createContext, useContext, useEffect, useState } from 'react';
import { onAuthStateChanged, signInWithPopup, signOut as fbSignOut } from 'firebase/auth';
import { auth, provider } from '../firebase';
import { api, ApiError } from '../api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user,    setUser]    = useState(null);   // Firebase user object
  const [profile, setProfile] = useState(null);   // { uid, email, name, role }
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState(null);

  const getToken = () => auth.currentUser?.getIdToken(false) ?? Promise.reject(new Error('Not authenticated'));

  async function loadProfile() {
    try {
      const data = await api.post('/api/auth/me', {}, getToken);
      setProfile(data);
      setError(null);
    } catch (err) {
      setError(err.message);
      setProfile(null);
    }
  }

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (firebaseUser) => {
      setUser(firebaseUser);
      if (firebaseUser) {
        await loadProfile();
      } else {
        setProfile(null);
      }
      setLoading(false);
    });
    return unsubscribe;
  }, []);

  async function signIn() {
    setError(null);
    try {
      await signInWithPopup(auth, provider);
      // onAuthStateChanged will fire and call loadProfile
    } catch (err) {
      setError(err.message);
    }
  }

  async function signOut() {
    await fbSignOut(auth);
    setProfile(null);
  }

  return (
    <AuthContext.Provider value={{ user, profile, loading, error, signIn, signOut, getToken }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider');
  return ctx;
}
