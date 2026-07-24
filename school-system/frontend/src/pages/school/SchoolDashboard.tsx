import { useEffect, useState } from 'react';
import { useAuthStore } from '@/store/auth';
import api from '@/services/api';
import type { DashboardAdmin, DashboardTeacher } from '@/types';
import clsx from 'clsx';
import {
  GraduationCap, Users, BookOpen, UserCheck, ClipboardList,
  Calendar, DollarSign, TrendingUp, Clock, Bell, Building2,
} from 'lucide-react';

export default function SchoolDashboard() {
  const user = useAuthStore((s) => s.user);
  const [adminData, setAdminData] = useState<DashboardAdmin | null>(null);
  const [teacherData, setTeacherData] = useState<DashboardTeacher | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchDashboard = async () => {
      try {
        if (user?.role === 'teacher') {
          const { data } = await api.get('/dashboard/teacher');
          setTeacherData(data);
        } else {
          const { data } = await api.get('/dashboard/admin');
          setAdminData(data);
        }
      } catch {
        // silent
      } finally {
        setLoading(false);
      }
    };
    fetchDashboard();
  }, [user?.role]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-emerald-500 border-t-transparent" />
      </div>
    );
  }

  if (user?.role === 'teacher' && teacherData) {
    return <TeacherDashboardView data={teacherData} />;
  }

  return <AdminDashboardView data={adminData} />;
}

function TeacherDashboardView({ data }: { data: DashboardTeacher }) {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-gray-900">My Dashboard</h2>
        <p className="text-sm text-gray-500">{data.today_timetable.length} lessons scheduled today</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <StatCard icon={BookOpen} label="Lessons Today" value={data.today_timetable.length} color="text-emerald-600" bg="bg-emerald-50" />
        <StatCard icon={ClipboardList} label="Pending Attendance" value={data.pending_attendance.length} color="text-amber-600" bg="bg-amber-50" />
        <StatCard icon={Calendar} label="Lessons This Week" value={data.lessons_this_week} color="text-blue-600" bg="bg-blue-50" />
      </div>

      <div className="card">
        <h3 className="text-base font-semibold text-gray-900 mb-4">Today's Timetable</h3>
        {data.today_timetable.length === 0 ? (
          <p className="text-sm text-gray-500 py-4 text-center">No lessons scheduled for today</p>
        ) : (
          <div className="space-y-2">
            {data.today_timetable.map((lesson, i) => (
              <div key={i} className="flex items-center gap-4 rounded-lg border border-gray-100 bg-gray-50 p-3">
                <div className="flex flex-col items-center">
                  <span className="text-sm font-bold text-gray-900">{lesson.start?.substring(0, 5)}</span>
                  <span className="text-xs text-gray-400">{lesson.end?.substring(0, 5)}</span>
                </div>
                <div className="h-8 w-px bg-gray-200" />
                <div>
                  <p className="text-sm font-medium text-gray-900">Class: {lesson.class_id?.substring(0, 8)}...</p>
                  <p className="text-xs text-gray-500">Room: {lesson.room || 'N/A'}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function AdminDashboardView({ data }: { data: DashboardAdmin | null }) {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-gray-900">School Dashboard</h2>
        <p className="text-sm text-gray-500">
          {new Date().toLocaleDateString('en-KE', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard icon={GraduationCap} label="Total Students" value={data?.total_students ?? '—'} color="text-emerald-600" bg="bg-emerald-50" />
        <StatCard icon={Users} label="Teachers" value={data?.total_teachers ?? '—'} color="text-blue-600" bg="bg-blue-50" />
        <StatCard icon={UserCheck} label="Attendance Today" value={data?.attendance_today?.percentage != null ? `${data.attendance_today.percentage}%` : '—'} color="text-violet-600" bg="bg-violet-50" />
        <StatCard icon={Building2} label="Classes" value={data?.total_classes ?? '—'} color="text-amber-600" bg="bg-amber-50" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Activity */}
        <div className="card">
          <h3 className="text-base font-semibold text-gray-900 mb-4">Recent Activity</h3>
          <div className="space-y-3">
            {[
              { label: 'Assessments (30d)', value: data?.recent_assessments ?? 0 },
              { label: 'Teachers', value: data?.total_teachers ?? 0 },
              { label: 'Students', value: data?.total_students ?? 0 },
              { label: 'Classes', value: data?.total_classes ?? 0 },
            ].map((item) => (
              <div key={item.label} className="flex items-center justify-between text-sm">
                <span className="text-gray-600">{item.label}</span>
                <span className="font-semibold text-gray-900">{item.value}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Quick Actions */}
        <div className="card">
          <h3 className="text-base font-semibold text-gray-900 mb-4">Quick Actions</h3>
          <div className="grid grid-cols-2 gap-3">
            {[
              { label: 'Register Student', icon: GraduationCap },
              { label: 'Add Teacher', icon: Users },
              { label: 'Take Attendance', icon: UserCheck },
              { label: 'Record Marks', icon: ClipboardList },
              { label: 'Create Exam', icon: BookOpen },
              { label: 'Generate Reports', icon: TrendingUp },
            ].map((action) => (
              <button
                key={action.label}
                className="flex items-center gap-2 rounded-lg border border-gray-200 bg-white px-3 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50 hover:border-gray-300 transition-colors"
              >
                <action.icon className="h-4 w-4 text-emerald-600" />
                {action.label}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function StatCard({ icon: Icon, label, value, color, bg }: {
  icon: React.ElementType; label: string; value: string | number; color: string; bg: string;
}) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm hover:shadow-md transition-shadow">
      <div className="flex items-center gap-3">
        <div className={clsx('rounded-lg p-2.5', bg)}>
          <Icon className={clsx('h-5 w-5', color)} />
        </div>
        <div>
          <p className="text-2xl font-bold text-gray-900">{value}</p>
          <p className="text-sm text-gray-500">{label}</p>
        </div>
      </div>
    </div>
  );
}


