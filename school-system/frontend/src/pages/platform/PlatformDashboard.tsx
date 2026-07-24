import { useEffect, useState } from 'react';
import { useAuthStore } from '@/store/auth';
import api from '@/services/api';
import {
  Building2, Users, GraduationCap, Shield, CheckCircle,
  Plus, Ban, DollarSign, Bell, Database,
} from 'lucide-react';
import clsx from 'clsx';

interface PlatformDashboardData {
  total_schools: number;
  active_schools: number;
  total_users: number;
  total_students: number;
  total_teachers: number;
  platform_admins: number;
  new_schools_30d: number;
  recent_audit_events_30d: number;
  top_school_by_students: {
    name: string | null;
    student_count: number;
  };
}

const defaultData: PlatformDashboardData = {
  total_schools: 0,
  active_schools: 0,
  total_users: 0,
  total_students: 0,
  total_teachers: 0,
  platform_admins: 0,
  new_schools_30d: 0,
  recent_audit_events_30d: 0,
  top_school_by_students: { name: null, student_count: 0 },
};

export default function PlatformDashboard() {
  const user = useAuthStore((s) => s.user);
  const [data, setData] = useState<PlatformDashboardData>(defaultData);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetch = async () => {
      try {
        const { data: d } = await api.get('/platform/dashboard');
        setData(d);
      } catch {
        setData(defaultData);
      } finally {
        setLoading(false);
      }
    };
    fetch();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-purple-500 border-t-transparent" />
      </div>
    );
  }

  const statCards = [
    {
      label: 'Total Schools', value: data.total_schools.toLocaleString(),
      icon: Building2, color: 'text-purple-400', bg: 'bg-purple-900/20',
      trend: `${data.new_schools_30d} new in 30 days`,
    },
    {
      label: 'Active Schools', value: data.active_schools.toLocaleString(),
      icon: CheckCircle, color: 'text-emerald-400', bg: 'bg-emerald-900/20',
      trend: `${((data.active_schools / (data.total_schools || 1)) * 100).toFixed(0)}% of total`,
    },
    {
      label: 'Total Students', value: data.total_students.toLocaleString(),
      icon: Users, color: 'text-amber-400', bg: 'bg-amber-900/20',
      trend: 'Across all schools',
    },
    {
      label: 'Total Teachers', value: data.total_teachers.toLocaleString(),
      icon: GraduationCap, color: 'text-blue-400', bg: 'bg-blue-900/20',
      trend: `${data.total_teachers > 0 ? ((data.total_students / data.total_teachers) || 0).toFixed(1) + ':1 student/teacher' : 'No teachers'}`,
    },
    {
      label: 'Platform Users', value: data.total_users.toLocaleString(),
      icon: Users, color: 'text-cyan-400', bg: 'bg-cyan-900/20',
      trend: `${data.platform_admins} admins`,
    },
    {
      label: 'Audit Events (30d)', value: data.recent_audit_events_30d.toLocaleString(),
      icon: Shield, color: 'text-violet-400', bg: 'bg-violet-900/20',
      trend: 'Platform-wide audit trail',
    },
    {
      label: 'Top School', value: data.top_school_by_students.name || 'N/A',
      icon: Building2, color: 'text-emerald-400', bg: 'bg-emerald-900/20',
      trend: `${data.top_school_by_students.student_count} students`,
    },
  ];

  const quickActions = [
    { label: 'Add School', icon: Plus, color: 'bg-purple-600 hover:bg-purple-700' },
    { label: 'Suspend School', icon: Ban, color: 'bg-red-600 hover:bg-red-700' },
    { label: 'View Revenue', icon: DollarSign, color: 'bg-emerald-600 hover:bg-emerald-700' },
    { label: 'Audit Logs', icon: Shield, color: 'bg-blue-600 hover:bg-blue-700' },
    { label: 'Broadcast', icon: Bell, color: 'bg-amber-600 hover:bg-amber-700' },
    { label: 'Backup', icon: Database, color: 'bg-violet-600 hover:bg-violet-700' },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold text-white">Platform Dashboard</h2>
        <p className="text-sm text-gray-500 mt-1">
          SaaS overview &mdash; {new Date().toLocaleDateString('en-KE', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
        </p>
      </div>

      {/* Quick Actions */}
      <div className="flex flex-wrap gap-2">
        {quickActions.map((action) => (
          <button
            key={action.label}
            className={clsx(
              'inline-flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium text-white shadow-lg transition-all',
              action.color
            )}
          >
            <action.icon className="h-4 w-4" />
            {action.label}
          </button>
        ))}
      </div>

      {/* Stat cards grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">
        {statCards.map((card) => (
          <div key={card.label} className="rounded-xl border border-gray-800 bg-gray-900 p-5 shadow-sm hover:border-gray-700 transition-colors">
            <div className="flex items-start justify-between">
              <div className={clsx('rounded-lg p-2', card.bg)}>
                <card.icon className={clsx('h-5 w-5', card.color)} />
              </div>
            </div>
            <p className="mt-3 text-2xl font-bold text-white">{card.value}</p>
            <p className="mt-0.5 text-sm text-gray-400">{card.label}</p>
            <p className="mt-1 text-xs text-gray-600">{card.trend}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top School Card */}
        <div className="rounded-xl border border-gray-800 bg-gray-900 p-5">
          <h3 className="text-base font-semibold text-white mb-4">Largest School</h3>
          {data.top_school_by_students.name ? (
            <div className="flex items-center gap-4">
              <div className="flex h-14 w-14 items-center justify-center rounded-xl bg-emerald-900/30">
                <Building2 className="h-7 w-7 text-emerald-400" />
              </div>
              <div>
                <p className="text-lg font-bold text-white">{data.top_school_by_students.name}</p>
                <p className="text-sm text-gray-400">{data.top_school_by_students.student_count} students enrolled</p>
              </div>
            </div>
          ) : (
            <p className="text-sm text-gray-500 py-4 text-center">No schools registered yet</p>
          )}
        </div>

        {/* Quick Stats Summary */}
        <div className="rounded-xl border border-gray-800 bg-gray-900 p-5">
          <h3 className="text-base font-semibold text-white mb-4">Platform Summary</h3>
          <div className="space-y-3">
            {[
              { label: 'New Schools (30d)', value: data.new_schools_30d },
              { label: 'Total Students', value: data.total_students },
              { label: 'Total Teachers', value: data.total_teachers },
              { label: 'Platform Admins', value: data.platform_admins },
              { label: 'Audit Events (30d)', value: data.recent_audit_events_30d },
            ].map((item) => (
              <div key={item.label} className="flex items-center justify-between py-1.5">
                <span className="text-sm text-gray-300">{item.label}</span>
                <span className="text-sm font-semibold text-white">{item.value.toLocaleString()}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
