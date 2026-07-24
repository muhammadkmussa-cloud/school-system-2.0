import { useEffect, useState } from 'react';
import { useAuthStore } from '@/store/auth';
import api from '@/services/api';
import type { DashboardAdmin, DashboardTeacher } from '@/types';
import {
  GraduationCap,
  Users,
  BookOpen,
  UserCheck,
  ClipboardList,
  Calendar,
} from 'lucide-react';

export default function DashboardPage() {
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
      } catch (err) {
        console.error('Failed to load dashboard', err);
      } finally {
        setLoading(false);
      }
    };
    fetchDashboard();
  }, [user?.role]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand-600 border-t-transparent" />
      </div>
    );
  }

  const isTeacher = user?.role === 'teacher';

  return (
    <div>
      <div className="page-header">
        <h2 className="text-2xl font-bold text-gray-900">Dashboard</h2>
        <p className="text-sm text-gray-500">
          {new Date().toLocaleDateString('en-KE', {
            weekday: 'long',
            year: 'numeric',
            month: 'long',
            day: 'numeric',
          })}
        </p>
      </div>

      {isTeacher && teacherData ? (
        <>
          {/* Teacher stats */}
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 mb-8">
            <div className="stat-card">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-100">
                  <Calendar className="h-5 w-5 text-blue-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-gray-900">
                    {teacherData.today_timetable.length}
                  </p>
                  <p className="text-sm text-gray-500">Lessons Today</p>
                </div>
              </div>
            </div>
            <div className="stat-card">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-amber-100">
                  <UserCheck className="h-5 w-5 text-amber-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-gray-900">
                    {teacherData.pending_attendance.length}
                  </p>
                  <p className="text-sm text-gray-500">Pending Attendance</p>
                </div>
              </div>
            </div>
            <div className="stat-card">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-green-100">
                  <ClipboardList className="h-5 w-5 text-green-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-gray-900">
                    {teacherData.lessons_this_week}
                  </p>
                  <p className="text-sm text-gray-500">Lessons This Week</p>
                </div>
              </div>
            </div>
          </div>

          {/* Today's Timetable */}
          {teacherData.today_timetable.length > 0 && (
            <div className="card">
              <h3 className="mb-4 text-lg font-semibold text-gray-900">
                Today's Timetable
              </h3>
              <div className="divide-y divide-gray-100">
                {teacherData.today_timetable.map((entry, i) => (
                  <div key={i} className="flex items-center gap-4 py-3">
                    <span className="text-sm font-medium text-brand-600 w-20">
                      {entry.start} - {entry.end}
                    </span>
                    <span className="text-sm text-gray-700">
                      Class {entry.class_id?.slice(0, 8)}
                    </span>
                    {entry.room && (
                      <span className="text-xs text-gray-400 ml-auto">
                        Room {entry.room}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      ) : adminData ? (
        <>
          {/* Admin stats */}
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4 mb-8">
            <div className="stat-card">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-100">
                  <GraduationCap className="h-5 w-5 text-blue-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-gray-900">
                    {adminData.total_students}
                  </p>
                  <p className="text-sm text-gray-500">Total Students</p>
                </div>
              </div>
            </div>
            <div className="stat-card">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-purple-100">
                  <Users className="h-5 w-5 text-purple-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-gray-900">
                    {adminData.total_teachers}
                  </p>
                  <p className="text-sm text-gray-500">Teachers</p>
                </div>
              </div>
            </div>
            <div className="stat-card">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-amber-100">
                  <UserCheck className="h-5 w-5 text-amber-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-gray-900">
                    {adminData.attendance_today.percentage}%
                  </p>
                  <p className="text-sm text-gray-500">Today's Attendance</p>
                </div>
              </div>
            </div>
            <div className="stat-card">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-green-100">
                  <BookOpen className="h-5 w-5 text-green-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-gray-900">
                    {adminData.total_classes}
                  </p>
                  <p className="text-sm text-gray-500">Classes</p>
                </div>
              </div>
            </div>
          </div>

          {/* Recent activity feed */}
          <div className="card">
            <h3 className="mb-4 text-lg font-semibold text-gray-900">
              Recent Activity
            </h3>
            <p className="text-sm text-gray-500">
              {adminData.recent_assessments} assessments recorded in the last 30 days.
            </p>
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              <div className="rounded-lg bg-green-50 p-4">
                <p className="text-sm font-medium text-green-800">
                  Attendance Today
                </p>
                <p className="text-2xl font-bold text-green-900 mt-1">
                  {adminData.attendance_today.present} / {adminData.attendance_today.total}
                </p>
                <p className="text-xs text-green-600 mt-1">students present</p>
              </div>
              <div className="rounded-lg bg-blue-50 p-4">
                <p className="text-sm font-medium text-blue-800">
                  Recent Assessments
                </p>
                <p className="text-2xl font-bold text-blue-900 mt-1">
                  {adminData.recent_assessments}
                </p>
                <p className="text-xs text-blue-600 mt-1">in the last 30 days</p>
              </div>
            </div>
          </div>
        </>
      ) : (
        <div className="card">
          <p className="text-gray-500">No dashboard data available.</p>
        </div>
      )}
    </div>
  );
}
