import { useAuth } from '../contexts/AuthContext';

export default function Profile() {
  const { profile, signOut } = useAuth();
  const initials = profile?.name?.charAt(0)?.toUpperCase() || profile?.email?.charAt(0)?.toUpperCase() || 'U';
  const isAdmin  = profile?.role === 'admin';

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
          <Row label="Email"    value={profile?.email || '—'} />
          <Row label="Name"     value={profile?.name  || '—'} />
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
