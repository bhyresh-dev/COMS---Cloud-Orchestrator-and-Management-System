import { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { api } from '../api';

export default function Profile() {
  const { profile, signOut, getToken, setProfile } = useAuth();
  const initials = profile?.name?.charAt(0)?.toUpperCase() || profile?.email?.charAt(0)?.toUpperCase() || 'U';
  const isAdmin  = profile?.role === 'admin';

  const [editing,  setEditing]  = useState(false);
  const [nameVal,  setNameVal]  = useState(profile?.name || '');
  const [saving,   setSaving]   = useState(false);
  const [error,    setError]    = useState(null);

  async function saveName() {
    if (!nameVal.trim() || nameVal.trim() === profile?.name) { setEditing(false); return; }
    setSaving(true); setError(null);
    try {
      const updated = await api.patch('/api/auth/me', { name: nameVal.trim() }, getToken);
      setProfile(updated);
      setEditing(false);
    } catch (err) {
      setError(err.message);
    } finally { setSaving(false); }
  }

  function cancelEdit() {
    setNameVal(profile?.name || '');
    setEditing(false);
    setError(null);
  }

  return (
    <div className="min-h-full bg-[#080b14] px-8 py-10">
      <div className="max-w-lg">
        <h1 className="text-2xl font-semibold text-white tracking-tight mb-8">Profile</h1>

        {/* Avatar + name */}
        <div className="flex items-center gap-5 mb-8">
          <div className="w-16 h-16 rounded-full bg-gradient-to-br from-pink-500 to-violet-600 flex items-center justify-center text-white text-2xl font-bold shadow-lg shadow-violet-900/40">
            {initials}
          </div>
          <div>
            <p className="text-white font-semibold text-lg">{profile?.name || profile?.email?.split('@')[0] || 'User'}</p>
            <span className={[
              'text-xs px-2.5 py-0.5 rounded-full border mt-1 inline-block',
              isAdmin
                ? 'bg-indigo-500/15 text-indigo-400 border-indigo-500/25'
                : 'bg-white/[0.06] text-white/45 border-white/[0.08]',
            ].join(' ')}>
              {profile?.role || 'user'}
            </span>
          </div>
        </div>

        {/* Details card */}
        <div className="bg-[#0d0f17] border border-white/[0.07] rounded-2xl divide-y divide-white/[0.05]">
          {/* Editable name row */}
          <div className="flex items-center gap-4 px-5 py-4">
            <span className="text-xs text-white/30 w-24 flex-shrink-0">Name</span>
            {editing ? (
              <div className="flex-1 flex items-center gap-2">
                <input
                  autoFocus
                  value={nameVal}
                  onChange={e => setNameVal(e.target.value)}
                  onKeyDown={e => { if (e.key === 'Enter') saveName(); if (e.key === 'Escape') cancelEdit(); }}
                  className="flex-1 bg-white/[0.06] border border-white/[0.12] rounded-lg px-3 py-1.5 text-sm text-white/90 outline-none focus:border-violet-500/50 transition-colors"
                />
                <button onClick={saveName} disabled={saving || !nameVal.trim()}
                  className="text-xs px-3 py-1.5 bg-violet-600/30 hover:bg-violet-600/50 border border-violet-500/30 text-violet-300 rounded-lg transition-colors disabled:opacity-40">
                  {saving ? 'Saving…' : 'Save'}
                </button>
                <button onClick={cancelEdit}
                  className="text-xs px-3 py-1.5 text-white/35 hover:text-white/60 transition-colors">
                  Cancel
                </button>
              </div>
            ) : (
              <div className="flex-1 flex items-center justify-between">
                <span className="text-sm text-white/70">{profile?.name || '—'}</span>
                <button onClick={() => { setNameVal(profile?.name || ''); setEditing(true); }}
                  className="text-xs text-white/25 hover:text-violet-400 transition-colors">
                  Edit
                </button>
              </div>
            )}
          </div>

          {error && (
            <div className="px-5 py-2 text-xs text-red-400">{error}</div>
          )}

          <Row label="Email"    value={profile?.email || '—'} />
          <Row label="Role"     value={profile?.role  || 'user'} />
          <Row label="User ID"  value={profile?.uid   || '—'} mono />
          <Row label="Provider" value="Google (Firebase)" />
        </div>

        {/* Logout */}
        <button
          onClick={signOut}
          className="mt-6 w-full flex items-center justify-center gap-2 px-4 py-3 bg-red-500/10 hover:bg-red-500/20 border border-red-500/20 hover:border-red-500/35 rounded-xl text-sm font-medium text-red-400 transition-all"
        >
          Sign out
        </button>
      </div>
    </div>
  );
}

function Row({ label, value, mono = false }) {
  return (
    <div className="flex items-center gap-4 px-5 py-4">
      <span className="text-xs text-white/30 w-24 flex-shrink-0">{label}</span>
      <span className={`text-sm flex-1 break-all ${mono ? 'font-mono text-white/45 text-xs' : 'text-white/70'}`}>{value}</span>
    </div>
  );
}
