import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

const ZapIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" stroke="none">
    <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" />
  </svg>
);

export default function Login() {
  const { user, profile, loading, error, signIn } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (!loading && user && profile) navigate('/dashboard', { replace: true });
  }, [user, profile, loading, navigate]);

  return (
    <div className="min-h-screen hero-gradient flex items-center justify-center px-4 relative">
      {/* Centered card */}
      <div className="relative z-10 w-full max-w-sm">
        <div className="bg-white/[0.06] backdrop-blur-2xl border border-white/[0.15] rounded-2xl px-8 py-10 shadow-2xl shadow-black/40 ring-1 ring-inset ring-white/[0.06]">

          {/* Logo */}
          <div className="flex items-center gap-2.5 mb-8">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-violet-900/50 text-white">
              <ZapIcon />
            </div>
            <span className="text-white font-semibold text-base tracking-tight">COMS</span>
          </div>

          <h1 className="text-xl font-semibold text-[#f0eeff] mb-1 tracking-tight">
            Welcome back
          </h1>
          <p className="text-sm text-[#9b8ec4] mb-8">
            Sign in to access your cloud resources.
          </p>

          {error && (
            <div className="mb-5 px-4 py-3 bg-red-500/10 border border-red-500/20 rounded-xl text-sm text-red-400">
              {error}
            </div>
          )}

          <button
            onClick={signIn}
            disabled={loading}
            className="w-full flex items-center justify-center gap-3 px-4 py-2.5 bg-white/[0.08] hover:bg-white/[0.14] border border-white/[0.15] hover:border-violet-400/40 rounded-xl text-sm font-medium text-[#f0eeff] transition-all disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <GoogleIcon />
            Continue with Google
          </button>

          <p className="mt-6 text-xs text-white/22 text-center">
            <span className="text-[#6b5fa0]">Access is restricted to authorized accounts only.</span>
          </p>
        </div>
      </div>
    </div>
  );
}

function GoogleIcon() {
  return (
    <svg width="17" height="17" viewBox="0 0 18 18" aria-hidden="true">
      <path d="M16.51 8H8.98v3h4.3c-.18 1-.74 1.48-1.6 2.04v2.01h2.6a7.8 7.8 0 0 0 2.38-5.88c0-.57-.05-.66-.15-1.18z" fill="#4285F4" />
      <path d="M8.98 17c2.16 0 3.97-.72 5.3-1.94l-2.6-2.04a4.8 4.8 0 0 1-7.18-2.54H1.83v2.07A8 8 0 0 0 8.98 17z" fill="#34A853" />
      <path d="M4.5 10.48A4.84 4.84 0 0 1 4.5 7.5V5.43H1.83a8 8 0 0 0 0 7.12l2.67-2.07z" fill="#FBBC05" />
      <path d="M8.98 3.18c1.17 0 2.23.4 3.06 1.2l2.3-2.3A8 8 0 0 0 1.83 5.43L4.5 7.5c.67-2 2.52-4.32 4.48-4.32z" fill="#EA4335" />
    </svg>
  );
}
