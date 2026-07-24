import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import { useAuthStore } from '@/store/auth';
import {
  LayoutDashboard, Users, GraduationCap, BookOpen, Calendar,
  UserCheck, ClipboardCheck, BookMarked, FileBarChart, Building2,
  LogOut, Menu, X, Wrench, ArrowUpDown, Upload,
  GitBranch, Shield, Globe, ClipboardList, Bell, CreditCard,
} from 'lucide-react';
import { useState } from 'react';
import clsx from 'clsx';

interface NavItem {
  to: string; icon: React.ElementType; label: string; end?: boolean;
}

const navItems: NavItem[] = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard', end: true },
  { to: '/students', icon: GraduationCap, label: 'Students' },
  { to: '/teachers', icon: Users, label: 'Teachers' },
  { to: '/academic', icon: Building2, label: 'Academic' },
  { to: '/timetable', icon: Calendar, label: 'Timetable' },
  { to: '/attendance', icon: UserCheck, label: 'Attendance' },
  { to: '/gradebook', icon: ClipboardCheck, label: 'Gradebook' },
  { to: '/lessons', icon: BookOpen, label: 'Lessons' },
  { to: '/reports', icon: FileBarChart, label: 'Reports' },
  { to: '/calendar', icon: Calendar, label: 'Calendar' },
];

const adminExtended: NavItem[] = [
  { to: '/exams', icon: BookMarked, label: 'Exams' },
  { to: '/assignments', icon: ClipboardList, label: 'Assignments' },
  { to: '/workflow', icon: GitBranch, label: 'Workflows' },
  { to: '/curriculum', icon: Globe, label: 'Curriculum' },
];

const platformNav: NavItem[] = [
  { to: '/schools', icon: Building2, label: 'Schools' },
  { to: '/audit', icon: Shield, label: 'Audit Trail' },
];

const adminTools: NavItem[] = [
  { to: '/setup', icon: Wrench, label: 'Setup Wizard' },
  { to: '/promotion', icon: ArrowUpDown, label: 'Promotion' },
  { to: '/import', icon: Upload, label: 'Import' },
  { to: '/billing', icon: CreditCard, label: 'Billing' },
];

export default function AppLayout() {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const isPlatformAdmin = user?.role === 'platform_admin';
  const isAdmin = user?.role === 'school_admin' || isPlatformAdmin;

  const items = [
    ...navItems,
    ...(isAdmin ? adminExtended : []),
    ...(isPlatformAdmin ? platformNav : []),
  ];
  const toolItems = isAdmin ? adminTools : [];

  return (
    <div className="flex h-screen overflow-hidden bg-gray-50">
      {sidebarOpen && (
        <div className="fixed inset-0 z-40 bg-black/50 lg:hidden"
          onClick={() => setSidebarOpen(false)} />
      )}

      <aside className={clsx(
        'fixed inset-y-0 left-0 z-50 flex w-64 flex-col border-r border-gray-200 bg-white transition-transform lg:static lg:translate-x-0',
        sidebarOpen ? 'translate-x-0' : '-translate-x-full'
      )}>
        <div className="flex h-16 items-center gap-3 border-b border-gray-200 px-6">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-600 text-white font-bold text-sm">EF</div>
          <span className="text-lg font-bold text-gray-900">School Management System</span>
          <button className="ml-auto lg:hidden" onClick={() => setSidebarOpen(false)}>
            <X className="h-5 w-5 text-gray-500" />
          </button>
        </div>

        <nav className="flex-1 overflow-y-auto px-3 py-4">
          <ul className="space-y-1">
            {items.map((item) => (
              <li key={item.to}>
                <NavLink to={item.to} end={item.end}
                  className={({ isActive }) => clsx(
                    'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                    isActive ? 'bg-brand-50 text-brand-700' : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                  )}
                  onClick={() => setSidebarOpen(false)}>
                  <item.icon className="h-5 w-5 flex-shrink-0" />
                  {item.label}
                </NavLink>
              </li>
            ))}
            {toolItems.length > 0 && (
              <>
                <li className="pt-3 pb-1">
                  <span className="px-3 text-xs font-semibold uppercase text-gray-400">Tools</span>
                </li>
                {toolItems.map((item) => (
                  <li key={item.to}>
                    <NavLink to={item.to}
                      className={({ isActive }) => clsx(
                        'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                        isActive ? 'bg-brand-50 text-brand-700' : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                      )}
                      onClick={() => setSidebarOpen(false)}>
                      <item.icon className="h-5 w-5 flex-shrink-0" />
                      {item.label}
                    </NavLink>
                  </li>
                ))}
              </>
            )}
          </ul>
        </nav>

        <div className="border-t border-gray-200 p-4">
          <div className="mb-2 text-xs text-gray-500">{user?.email}</div>
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-gray-700">{user?.full_name}</span>
            <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600 capitalize">
              {user?.role.replace('_', ' ')}
            </span>
          </div>
          <button onClick={handleLogout}
            className="mt-3 flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-red-600 hover:bg-red-50 transition-colors">
            <LogOut className="h-4 w-4" /> Sign out
          </button>
        </div>
      </aside>

      <div className="flex flex-1 flex-col overflow-hidden">
        <header className="flex h-16 items-center gap-4 border-b border-gray-200 bg-white px-6">
          <button className="lg:hidden" onClick={() => setSidebarOpen(true)}>
            <Menu className="h-6 w-6 text-gray-600" />
          </button>
          <h1 className="text-lg font-semibold text-gray-900">
            {user?.role === 'platform_admin' ? 'Platform Administration' :
             user?.role === 'school_admin' ? 'School Administration' :
             'Teacher Dashboard'}
          </h1>
        </header>
        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}