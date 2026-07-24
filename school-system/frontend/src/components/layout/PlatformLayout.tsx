import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import { useAuthStore } from '@/store/auth';
import {
  LayoutDashboard, Building2, CreditCard, Receipt, Users,
  Shield, Activity, FileText, Bell, Settings, Database,
  Server, BarChart3, Globe, Terminal, HardDrive, Key,
  LogOut, Menu, X, ChevronDown, ChevronRight, RefreshCw,
} from 'lucide-react';
import { useState } from 'react';
import clsx from 'clsx';

const navSections = [
  {
    title: 'Platform',
    items: [
      { to: '/admin', icon: LayoutDashboard, label: 'Dashboard', end: true },
      { to: '/admin/schools', icon: Building2, label: 'Schools' },
    ],
  },
  {
    title: 'Business',
    items: [
      { to: '/admin/subscriptions', icon: CreditCard, label: 'Subscriptions' },
      { to: '/admin/plans', icon: Receipt, label: 'Plans & Pricing' },
      { to: '/admin/revenue', icon: BarChart3, label: 'Revenue' },
      { to: '/admin/invoices', icon: FileText, label: 'Invoices' },
      { to: '/admin/payments', icon: Activity, label: 'Payments' },
    ],
  },
  {
    title: 'Administration',
    items: [
      { to: '/admin/users', icon: Users, label: 'Users' },
      { to: '/admin/roles', icon: Key, label: 'Roles & Permissions' },
      { to: '/admin/announcements', icon: Bell, label: 'Announcements' },
      { to: '/admin/support', icon: Globe, label: 'Support Tickets' },
    ],
  },
  {
    title: 'Operations',
    items: [
      { to: '/admin/analytics', icon: BarChart3, label: 'Platform Analytics' },
      { to: '/admin/monitoring', icon: Activity, label: 'API Monitoring' },
      { to: '/admin/audit', icon: Shield, label: 'Audit Logs' },
      { to: '/admin/health', icon: Server, label: 'System Health' },
      { to: '/admin/database', icon: Database, label: 'Database Status' },
      { to: '/admin/jobs', icon: Terminal, label: 'Background Jobs' },
    ],
  },
  {
    title: 'Configuration',
    items: [
      { to: '/admin/integrations', icon: Globe, label: 'Integrations' },
      { to: '/admin/feature-flags', icon: HardDrive, label: 'Feature Flags' },
      { to: '/admin/backups', icon: RefreshCw, label: 'Backup & Restore' },
      { to: '/admin/settings', icon: Settings, label: 'Settings' },
    ],
  },
];

export default function PlatformLayout() {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>(() => {
    const sections: Record<string, boolean> = {};
    navSections.forEach((s) => { sections[s.title] = true; });
    return sections;
  });

  const toggleSection = (title: string) => {
    setExpandedSections((prev) => ({ ...prev, [title]: !prev[title] }));
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="flex h-screen overflow-hidden bg-gray-950">
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div className="fixed inset-0 z-40 bg-black/70 lg:hidden"
          onClick={() => setSidebarOpen(false)} />
      )}

      {/* Sidebar */}
      <aside className={clsx(
        'fixed inset-y-0 left-0 z-50 flex w-72 flex-col border-r border-gray-800 bg-gray-900 transition-transform lg:static lg:translate-x-0',
        sidebarOpen ? 'translate-x-0' : '-translate-x-full'
      )}>
        {/* Logo */}
        <div className="flex h-16 items-center gap-3 border-b border-gray-800 px-6">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-purple-600 text-white font-bold text-sm shadow-lg shadow-purple-600/30">
            EF
          </div>
          <div>
            <span className="text-lg font-bold text-white">School Management System</span>
            <span className="ml-2 rounded bg-purple-600/20 px-1.5 py-0.5 text-[10px] font-medium text-purple-400 uppercase tracking-wider">
              Platform
            </span>
          </div>
          <button className="ml-auto lg:hidden" onClick={() => setSidebarOpen(false)}>
            <X className="h-5 w-5 text-gray-400" />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto px-4 py-4 scrollbar-thin scrollbar-track-gray-900 scrollbar-thumb-gray-700">
          {navSections.map((section) => (
            <div key={section.title} className="mb-3">
              <button
                onClick={() => toggleSection(section.title)}
                className="flex w-full items-center gap-2 px-2 py-1.5 text-xs font-semibold uppercase tracking-wider text-gray-500 hover:text-gray-300 transition-colors"
              >
                {expandedSections[section.title] ? (
                  <ChevronDown className="h-3 w-3" />
                ) : (
                  <ChevronRight className="h-3 w-3" />
                )}
                {section.title}
              </button>
              {expandedSections[section.title] && (
                <ul className="mt-1 space-y-0.5">
                  {section.items.map((item) => (
                    <li key={item.to}>
                      <NavLink
                        to={item.to}
                        end={item.end}
                        className={({ isActive }) => clsx(
                          'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-all',
                          isActive
                            ? 'bg-purple-600/15 text-purple-300 border-l-2 border-purple-500'
                            : 'text-gray-400 hover:bg-gray-800 hover:text-gray-200 border-l-2 border-transparent'
                        )}
                        onClick={() => setSidebarOpen(false)}
                      >
                        <item.icon className="h-4.5 w-4.5 flex-shrink-0" />
                        {item.label}
                      </NavLink>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          ))}
        </nav>

        {/* User section */}
        <div className="border-t border-gray-800 p-4">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-purple-600/20 text-purple-400 text-sm font-semibold">
              {user?.full_name?.charAt(0)?.toUpperCase() || 'U'}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-200 truncate">{user?.full_name}</p>
              <p className="text-xs text-gray-500 truncate">{user?.email}</p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="mt-3 flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-red-400 hover:bg-red-900/30 hover:text-red-300 transition-colors"
          >
            <LogOut className="h-4 w-4" /> Sign out
          </button>
        </div>
      </aside>

      {/* Main content */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Top bar */}
        <header className="flex h-16 items-center gap-4 border-b border-gray-800 bg-gray-900/80 backdrop-blur-sm px-6">
          <button className="lg:hidden" onClick={() => setSidebarOpen(true)}>
            <Menu className="h-6 w-6 text-gray-400" />
          </button>
          <div className="flex items-center gap-2 text-sm text-gray-400">
            <span className="text-purple-400">Platform Admin</span>
            <span className="text-gray-600">/</span>
            <span className="text-gray-300">Console</span>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto p-6 bg-gray-950">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
