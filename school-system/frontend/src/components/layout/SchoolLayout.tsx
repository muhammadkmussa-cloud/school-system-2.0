import { Outlet, NavLink, useNavigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '@/store/auth';
import {
  LayoutDashboard, Users, GraduationCap, BookOpen, Calendar,
  UserCheck, ClipboardCheck, BookMarked, FileBarChart, Building2,
  LogOut, Menu, X, Wrench, ArrowUpDown, Upload,
  GitBranch, Shield, Globe, ClipboardList, Bell, CreditCard,
  School, PieChart, MessageSquare, Library, Check, CheckSquare,
  AlertCircle, AlertTriangle
} from 'lucide-react';
import { useState, useEffect, useRef } from 'react';
import clsx from 'clsx';
import api from '@/services/api';
import { Notification } from '@/types';
import { useSubscriptionStore } from '@/store/subscription';

interface NavItem {
  to: string; icon: React.ElementType; label: string; end?: boolean;
}

const primaryNav: NavItem[] = [
  { to: '/school', icon: LayoutDashboard, label: 'Dashboard', end: true },
  { to: '/school/students', icon: GraduationCap, label: 'Students' },
  { to: '/school/admissions', icon: Users, label: 'Admissions' },
  { to: '/school/teachers', icon: Users, label: 'Teachers' },
  { to: '/school/academic', icon: Building2, label: 'Classes & Streams' },
  { to: '/school/subjects', icon: BookOpen, label: 'Subjects' },
  { to: '/school/timetable', icon: Calendar, label: 'Timetable' },
];

const academicNav: NavItem[] = [
  { to: '/school/attendance', icon: UserCheck, label: 'Attendance' },
  { to: '/school/lessons', icon: BookOpen, label: 'Lessons' },
  { to: '/school/assignments', icon: ClipboardList, label: 'Assignments' },
  { to: '/school/exams', icon: BookMarked, label: 'Exams' },
  { to: '/school/gradebook', icon: ClipboardCheck, label: 'Gradebook' },
  { to: '/school/curriculum', icon: Globe, label: 'Curriculum' },
];

const operationsNav: NavItem[] = [
  { to: '/school/reports', icon: FileBarChart, label: 'Reports' },
  { to: '/school/analytics', icon: PieChart, label: 'Analytics' },
  { to: '/school/calendar', icon: Calendar, label: 'Calendar' },
  { to: '/school/communication', icon: MessageSquare, label: 'Communication' },
  { to: '/school/library', icon: Library, label: 'Library' },
  { to: '/school/workflow', icon: GitBranch, label: 'Approvals' },
];

const toolsNav: NavItem[] = [
  { to: '/school/setup', icon: Wrench, label: 'Setup Wizard' },
  { to: '/school/promotion', icon: ArrowUpDown, label: 'Promotion' },
  { to: '/school/import', icon: Upload, label: 'Import' },
];

const getRoleLabel = (role?: string) => {
  switch (role) {
    case 'school_admin': return 'School Admin';
    case 'deputy_principal': return 'Deputy Principal';
    case 'head_teacher': return 'Head Teacher';
    case 'teacher': return 'Teacher';
    default: return role || 'Staff';
  }
};

const getRoleBadgeClasses = (role?: string) => {
  switch (role) {
    case 'school_admin': return 'bg-emerald-100 text-emerald-700 border border-emerald-200';
    case 'deputy_principal': return 'bg-blue-100 text-blue-700 border border-blue-200';
    case 'head_teacher': return 'bg-indigo-100 text-indigo-700 border border-indigo-200';
    case 'teacher': return 'bg-purple-100 text-purple-700 border border-purple-200';
    default: return 'bg-gray-100 text-gray-700 border border-gray-200';
  }
};

const getFilteredNavs = (role?: string) => {
  if (role === 'school_admin') {
    return {
      primary: primaryNav,
      academic: academicNav,
      operations: operationsNav,
      tools: toolsNav,
    };
  }

  if (role === 'deputy_principal') {
    return {
      primary: primaryNav.filter(item => ['Dashboard', 'Students', 'Admissions', 'Teachers', 'Classes & Streams'].includes(item.label)),
      academic: academicNav.filter(item => ['Attendance', 'Assignments', 'Gradebook'].includes(item.label)),
      operations: operationsNav.filter(item => ['Reports', 'Analytics', 'Calendar', 'Communication', 'Approvals'].includes(item.label)),
      tools: toolsNav.filter(item => ['Import'].includes(item.label)),
    };
  }

  if (role === 'head_teacher') {
    return {
      primary: primaryNav.filter(item => ['Dashboard', 'Teachers', 'Classes & Streams', 'Subjects', 'Timetable'].includes(item.label)),
      academic: academicNav.filter(item => ['Lessons', 'Assignments', 'Exams', 'Gradebook', 'Curriculum'].includes(item.label)),
      operations: operationsNav.filter(item => ['Reports', 'Analytics', 'Calendar', 'Approvals'].includes(item.label)),
      tools: [],
    };
  }

  // Fallback / Teacher
  return {
    primary: primaryNav.filter(item => ['Dashboard', 'Students', 'Timetable'].includes(item.label)),
    academic: academicNav.filter(item => ['Attendance', 'Lessons', 'Assignments', 'Exams', 'Gradebook'].includes(item.label)),
    operations: operationsNav.filter(item => ['Calendar', 'Communication'].includes(item.label)),
    tools: [],
  };
};

export default function SchoolLayout() {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // Notification States
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Subscription State
  const { status: subStatus, isReadOnly, message, daysLeft, fetchStatus } = useSubscriptionStore();

  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const formatTimeAgo = (dateStr: string) => {
    try {
      const date = new Date(dateStr);
      const now = new Date();
      const diffMs = now.getTime() - date.getTime();
      const diffMins = Math.floor(diffMs / 60000);
      const diffHours = Math.floor(diffMins / 60);
      const diffDays = Math.floor(diffHours / 24);

      if (diffMins < 1) return 'Just now';
      if (diffMins < 60) return `${diffMins}m ago`;
      if (diffHours < 24) return `${diffHours}h ago`;
      return `${diffDays}d ago`;
    } catch {
      return '';
    }
  };

  const fetchNotifications = async () => {
    try {
      const response = await api.get('/notifications');
      setNotifications(response.data.notifications || []);
      setUnreadCount(response.data.unread_count || 0);
    } catch (err) {
      console.error('Failed to fetch notifications', err);
    }
  };

  useEffect(() => {
    fetchNotifications();
    const interval = setInterval(fetchNotifications, 30000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setNotificationsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);

  const handleMarkRead = async (id: string) => {
    try {
      await api.post(`/notifications/${id}/read`);
      setNotifications(prev =>
        prev.map(n => n.id === id ? { ...n, read: true } : n)
      );
      setUnreadCount(prev => Math.max(0, prev - 1));
    } catch (err) {
      console.error('Failed to mark notification as read', err);
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await api.post('/notifications/read-all');
      setNotifications(prev => prev.map(n => ({ ...n, read: true })));
      setUnreadCount(0);
    } catch (err) {
      console.error('Failed to mark all notifications as read', err);
    }
  };

  const filteredNavs = getFilteredNavs(user?.role);

  const getPageTitle = () => {
    const allItems: NavItem[] = [...primaryNav, ...academicNav, ...operationsNav, ...toolsNav];
    const current = allItems.find((item) => {
      if (item.end) return location.pathname === item.to;
      return location.pathname.startsWith(item.to);
    });
    return current?.label || 'Dashboard';
  };

  const NavItems = ({ items }: { items: typeof primaryNav }) => (
    <ul className="space-y-0.5">
      {items.map((item) => (
        <li key={item.to}>
          <NavLink
            to={item.to}
            end={item.end}
            className={({ isActive }) => clsx(
              'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
              isActive
                ? 'bg-emerald-50 text-emerald-700 border-l-2 border-emerald-500'
                : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900 border-l-2 border-transparent'
            )}
            onClick={() => setSidebarOpen(false)}
          >
            <item.icon className="h-5 w-5 flex-shrink-0" />
            {item.label}
          </NavLink>
        </li>
      ))}
    </ul>
  );

  return (
    <div className="flex h-screen overflow-hidden bg-gray-50">
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div className="fixed inset-0 z-40 bg-black/40 lg:hidden"
          onClick={() => setSidebarOpen(false)} />
      )}

      {/* Sidebar */}
      <aside className={clsx(
        'fixed inset-y-0 left-0 z-50 flex w-64 flex-col border-r border-gray-200 bg-white transition-transform lg:static lg:translate-x-0',
        sidebarOpen ? 'translate-x-0' : '-translate-x-full'
      )}>
        {/* Logo */}
        <div className="flex h-16 items-center gap-3 border-b border-gray-200 px-5">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-emerald-600 text-white font-bold text-sm shadow-sm">
            EF
          </div>
          <div>
            <span className="text-base font-bold text-gray-900">School Management System</span>
            <span className="ml-1.5 text-xs text-gray-500 font-medium">{user?.full_name?.split(' ')[0] || ''}'s School</span>
          </div>
          <button className="ml-auto lg:hidden" onClick={() => setSidebarOpen(false)}>
            <X className="h-5 w-5 text-gray-400" />
          </button>
        </div>

        {/* Scrollable nav */}
        <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-5">
          {filteredNavs.primary.length > 0 && (
            <div>
              <p className="mb-1.5 px-3 text-[10px] font-semibold uppercase tracking-widest text-gray-400">Main</p>
              <NavItems items={filteredNavs.primary} />
            </div>
          )}
          {filteredNavs.academic.length > 0 && (
            <div>
              <p className="mb-1.5 px-3 text-[10px] font-semibold uppercase tracking-widest text-gray-400">Academic</p>
              <NavItems items={filteredNavs.academic} />
            </div>
          )}
          {filteredNavs.operations.length > 0 && (
            <div>
              <p className="mb-1.5 px-3 text-[10px] font-semibold uppercase tracking-widest text-gray-400">Operations</p>
              <NavItems items={filteredNavs.operations} />
            </div>
          )}
          {filteredNavs.tools.length > 0 && (
            <div>
              <p className="mb-1.5 px-3 text-[10px] font-semibold uppercase tracking-widest text-gray-400">Tools</p>
              <NavItems items={filteredNavs.tools} />
            </div>
          )}
        </nav>

        {/* User footer */}
        <div className="border-t border-gray-200 p-4">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-emerald-100 text-emerald-700 text-xs font-semibold">
              {user?.full_name?.charAt(0)?.toUpperCase() || 'U'}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-800 truncate">{user?.full_name}</p>
              <p className="text-xs text-gray-400 truncate">{user?.email}</p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="mt-3 flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-red-600 hover:bg-red-50 transition-colors"
          >
            <LogOut className="h-4 w-4" /> Sign out
          </button>
        </div>
      </aside>

      {/* Main area */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Top bar */}
        <header className="flex h-16 items-center gap-4 border-b border-gray-200 bg-white px-6">
          <button className="lg:hidden" onClick={() => setSidebarOpen(true)}>
            <Menu className="h-6 w-6 text-gray-500" />
          </button>
          <h1 className="text-lg font-semibold text-gray-900">{getPageTitle()}</h1>
          <div className="ml-auto flex items-center gap-4">
            {/* Notification Bell & Dropdown */}
            <div className="relative" ref={dropdownRef}>
              <button
                onClick={() => setNotificationsOpen(!notificationsOpen)}
                className="relative rounded-full p-2 text-gray-500 hover:bg-gray-100 hover:text-gray-700 transition-colors focus:outline-none"
                aria-label="Notifications"
              >
                <Bell className="h-5 w-5" />
                {unreadCount > 0 && (
                  <span className="absolute right-1.5 top-1.5 flex h-2 w-2 rounded-full bg-red-500 ring-2 ring-white animate-pulse" />
                )}
              </button>

              {notificationsOpen && (
                <div className="absolute right-0 mt-2 w-80 rounded-xl border border-gray-200 bg-white shadow-xl ring-1 ring-black/5 z-50 overflow-hidden">
                  {/* Header */}
                  <div className="flex items-center justify-between border-b border-gray-100 px-4 py-3 bg-gray-50/50">
                    <span className="text-sm font-semibold text-gray-900">Notifications</span>
                    {unreadCount > 0 && (
                      <button
                        onClick={handleMarkAllRead}
                        className="flex items-center gap-1 text-xs font-medium text-emerald-600 hover:text-emerald-700 transition-colors"
                      >
                        <Check className="h-3.5 w-3.5" /> Mark all read
                      </button>
                    )}
                  </div>

                  {/* Body */}
                  <div className="max-h-72 overflow-y-auto divide-y divide-gray-100">
                    {notifications.length === 0 ? (
                      <div className="flex flex-col items-center justify-center py-8 px-4 text-center">
                        <Bell className="h-8 w-8 text-gray-300 mb-2" />
                        <p className="text-sm font-medium text-gray-900">All caught up!</p>
                        <p className="text-xs text-gray-500">No new notifications.</p>
                      </div>
                    ) : (
                      notifications.map((n) => (
                        <div
                          key={n.id}
                          onClick={() => !n.read && handleMarkRead(n.id)}
                          className={clsx(
                            'p-4 transition-colors text-left cursor-pointer hover:bg-gray-50/80',
                            !n.read ? 'bg-emerald-50/20' : ''
                          )}
                        >
                          <div className="flex items-start justify-between gap-2">
                            <span className={clsx(
                              'text-xs font-semibold leading-none',
                              !n.read ? 'text-gray-900 font-bold' : 'text-gray-700'
                            )}>
                              {n.title}
                            </span>
                            <span className="text-[10px] text-gray-400 whitespace-nowrap">
                              {formatTimeAgo(n.created_at)}
                            </span>
                          </div>
                          <p className="mt-1 text-xs text-gray-500 line-clamp-2">
                            {n.body}
                          </p>
                          <div className="mt-2 flex items-center justify-between">
                            {n.priority && n.priority !== 'normal' && (
                              <span className={clsx(
                                'rounded px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wider',
                                n.priority === 'urgent' ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-700'
                              )}>
                                {n.priority}
                              </span>
                            )}
                            {!n.read && (
                              <span className="h-2 w-2 rounded-full bg-emerald-500 ml-auto" />
                            )}
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              )}
            </div>

            <span className={clsx("rounded-full px-2.5 py-0.5 text-xs font-semibold shadow-sm", getRoleBadgeClasses(user?.role))}>
              {getRoleLabel(user?.role)}
            </span>
          </div>
        </header>

        {/* Gating & Trial Banners */}
        {isReadOnly && (
          <div className="bg-gradient-to-r from-red-600 to-rose-600 text-white px-6 py-3 flex items-center justify-between shadow-md">
            <div className="flex items-center gap-3">
              <AlertTriangle className="h-5 w-5 text-red-100 flex-shrink-0 animate-pulse" />
              <div>
                <p className="text-sm font-semibold">School Management System Read-Only Mode</p>
                <p className="text-xs text-red-100">{message || 'Your trial or subscription has expired. All records are safe, but new records cannot be added.'}</p>
              </div>
            </div>
            <button
              onClick={() => navigate('/school/billing')}
              className="rounded-lg bg-white px-3 py-1.5 text-xs font-bold text-red-700 hover:bg-red-50 transition-colors shadow-sm whitespace-nowrap"
            >
              Subscribe Now
            </button>
          </div>
        )}

        {!isReadOnly && subStatus === 'trial' && daysLeft !== null && daysLeft <= 14 && (
          <div className="bg-gradient-to-r from-amber-500 to-orange-500 text-white px-6 py-3 flex items-center justify-between shadow-sm">
            <div className="flex items-center gap-3">
              <AlertCircle className="h-5 w-5 text-amber-100 flex-shrink-0" />
              <div>
                <p className="text-sm font-semibold">Free Trial Status</p>
                <p className="text-xs text-amber-100">You have {daysLeft} {daysLeft === 1 ? 'day' : 'days'} remaining in your trial. Upgrade to premium to preserve full access.</p>
              </div>
            </div>
            <button
              onClick={() => navigate('/school/billing')}
              className="rounded-lg bg-white px-3 py-1.5 text-xs font-bold text-amber-700 hover:bg-amber-50 transition-colors shadow-sm whitespace-nowrap"
            >
              Upgrade Plan
            </button>
          </div>
        )}

        {/* Content */}
        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
