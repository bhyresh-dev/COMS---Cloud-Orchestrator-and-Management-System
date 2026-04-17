import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

// ── Icons ────────────────────────────────────────────────────
const Icon = ({ d, size = 16, fill = 'none', stroke = 'currentColor' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill={fill} stroke={stroke} strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
    <path d={d} />
  </svg>
);
const HomeIcon    = () => <Icon d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z M9 22V12h6v10" />;
const SearchIcon  = () => <Icon d="M21 21l-4.35-4.35M17 11A6 6 0 1 1 5 11a6 6 0 0 1 12 0z" />;
const ShieldIcon  = () => <Icon d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />;
const GridIcon    = () => <Icon d="M3 3h7v7H3zM14 3h7v7h-7zM14 14h7v7h-7zM3 14h7v7H3z" />;
const StarIcon    = () => <Icon d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />;
const UserIcon    = () => <Icon d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2 M12 3a4 4 0 1 0 0 8 4 4 0 0 0 0-8z" />;
const UsersIcon   = () => <Icon d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2 M23 21v-2a4 4 0 0 0-3-3.87 M16 3.13a4 4 0 0 1 0 7.75" />;
const LogIcon     = () => <Icon d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z M14 2v6h6 M16 13H8 M16 17H8 M10 9H8" />;
const ChevronDown = () => <Icon d="M6 9l6 6 6-6" size={14} />;
const SidebarIcon = () => <Icon d="M3 3h18v18H3zM9 3v18" />;
const GiftIcon    = () => <Icon d="M20 12v10H4V12 M22 7H2v5h20V7z M12 22V7 M12 7H7.5a2.5 2.5 0 0 1 0-5C11 2 12 7 12 7z M12 7h4.5a2.5 2.5 0 0 0 0-5C13 2 12 7 12 7z" />;
const ZapIcon     = () => <Icon d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" fill="currentColor" stroke="none" />;
const BellIcon    = () => <Icon d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9 M13.73 21a2 2 0 0 1-3.46 0" />;

function NavItem({ icon, label, to, badge, onClick }) {
  const { pathname } = useLocation();
  const active = to && (pathname === to || pathname.startsWith(to + '/'));

  const cls = [
    'flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors cursor-pointer select-none',
    active
      ? 'bg-white/[0.08] text-white'
      : 'text-white/50 hover:bg-white/[0.05] hover:text-white/80',
  ].join(' ');

  const content = (
    <>
      <span className={active ? 'text-white/80' : 'text-white/35'}>{icon}</span>
      <span className="flex-1 font-medium">{label}</span>
      {badge && (
        <span className="flex items-center gap-0.5 text-[10px] text-white/30 bg-white/[0.07] px-1.5 py-0.5 rounded">
          {badge}
        </span>
      )}
    </>
  );

  return to
    ? <Link to={to} className={cls}>{content}</Link>
    : <div className={cls} onClick={onClick}>{content}</div>;
}

function SectionLabel({ children }) {
  return (
    <p className="px-3 pt-4 pb-1 text-[11px] font-semibold text-white/25 uppercase tracking-widest">
      {children}
    </p>
  );
}

export default function Layout({ children }) {
  const { profile, signOut } = useAuth();
  const isAdmin = profile?.role === 'admin';
  const initials = profile?.name?.charAt(0)?.toUpperCase() || profile?.email?.charAt(0)?.toUpperCase() || 'U';

  return (
    <div className="flex h-screen bg-[#080b14] overflow-hidden">

      {/* ── Sidebar ──────────────────────────────────────────── */}
      <aside className="w-[260px] flex-shrink-0 flex flex-col h-full bg-[#0d0f17] border-r border-white/[0.07]">

        {/* Logo row */}
        <div className="h-14 flex items-center justify-between px-4 flex-shrink-0">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-violet-900/40">
              <ZapIcon />
            </div>
            <span className="text-white font-semibold text-sm tracking-tight">COMS</span>
          </div>
          <button className="text-white/25 hover:text-white/50 transition-colors">
            <SidebarIcon />
          </button>
        </div>

        {/* Workspace selector */}
        <div className="px-3 mb-1 flex-shrink-0">
          <div className="flex items-center gap-2.5 px-3 py-2 rounded-lg hover:bg-white/[0.05] cursor-pointer transition-colors">
            <div className="w-5 h-5 rounded bg-blue-600 flex items-center justify-center text-white text-[11px] font-bold flex-shrink-0">
              {initials}
            </div>
            <span className="flex-1 text-sm text-white/70 truncate font-medium">
              {profile?.email?.split('@')[0] || 'Workspace'}
            </span>
            <ChevronDown />
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 overflow-y-auto px-3 pb-3 space-y-0.5">
          <NavItem icon={<HomeIcon />}   label="Home"      to="/dashboard" />
          <NavItem icon={<SearchIcon />} label="Search"    badge="Ctrl K" />
          <NavItem icon={<LogIcon />}    label="Audit Log" to="/audit"  />
          <NavItem icon={<ShieldIcon />} label="Security"  to="/security" />

          <SectionLabel>Resources</SectionLabel>
          <NavItem icon={<GridIcon />}   label="All Resources"      to="/dashboard" />
          <NavItem icon={<StarIcon />}   label="My Buckets"         to="/dashboard" />
          <NavItem icon={<UserIcon />}   label="Approvals"          to="/approvals" />
          {isAdmin && (
            <NavItem icon={<UsersIcon />} label="Admin Dashboard" to="/admin" />
          )}

          {/* Recents placeholder */}
          <SectionLabel>Recents</SectionLabel>
          <p className="px-3 py-1.5 text-xs text-white/20">No recent activity</p>
        </nav>

        {/* Bottom cards */}
        <div className="px-3 pb-3 space-y-2 flex-shrink-0 border-t border-white/[0.06] pt-3">
          {/* Info card */}
          <div className="flex items-center gap-3 bg-white/[0.04] border border-white/[0.06] rounded-xl px-3 py-3">
            <div className="flex-1 min-w-0">
              <p className="text-xs font-semibold text-white/80">Audit Trail</p>
              <p className="text-[11px] text-white/35 mt-0.5">All actions are logged</p>
            </div>
            <div className="w-8 h-8 rounded-lg bg-white/[0.06] flex items-center justify-center text-white/40 flex-shrink-0">
              <GiftIcon />
            </div>
          </div>

          {/* Admin card */}
          {isAdmin && (
            <div className="flex items-center gap-3 bg-white/[0.04] border border-white/[0.06] rounded-xl px-3 py-3">
              <div className="flex-1 min-w-0">
                <p className="text-xs font-semibold text-white/80">Admin Mode</p>
                <p className="text-[11px] text-white/35 mt-0.5">Full platform access</p>
              </div>
              <div className="w-8 h-8 rounded-full bg-indigo-600 flex items-center justify-center flex-shrink-0 shadow-lg shadow-indigo-900/50">
                <ZapIcon />
              </div>
            </div>
          )}

          {/* User row */}
          <div className="flex items-center justify-between px-1 pt-1">
            <div className="flex items-center gap-2.5">
              <div className="w-7 h-7 rounded-full bg-gradient-to-br from-pink-500 to-violet-600 flex items-center justify-center text-white text-xs font-bold">
                {initials}
              </div>
              <span className="text-xs text-white/40 truncate max-w-[130px]">{profile?.email}</span>
            </div>
            <button
              onClick={signOut}
              className="text-white/25 hover:text-white/60 transition-colors"
              title="Sign out"
            >
              <BellIcon />
            </button>
          </div>
        </div>
      </aside>

      {/* ── Main ─────────────────────────────────────────────── */}
      <main className="flex-1 min-w-0 overflow-y-auto">
        {children}
      </main>
    </div>
  );
}
