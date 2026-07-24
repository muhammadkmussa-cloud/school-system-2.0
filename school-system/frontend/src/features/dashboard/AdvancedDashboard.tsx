import { useEffect, useState } from 'react';
import api from '@/services/api';
import toast from 'react-hot-toast';
import {
  TrendingUp, TrendingDown, AlertTriangle, Award,
  Users, GraduationCap, BookOpen, Activity, Target,
} from 'lucide-react';

export default function AdvancedDashboard() {
  const [summary, setSummary] = useState<any>(null);
  const [heatmap, setHeatmap] = useState<any>(null);
  const [atRisk, setAtRisk] = useState<any[]>([]);
  const [leaderboard, setLeaderboard] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'summary' | 'heatmap' | 'risk' | 'leaders'>('summary');

  useEffect(() => {
    const load = async () => {
      try {
        const [sum] = await Promise.all([
          api.get('/dashboard/advanced/executive-summary'),
        ]);
        setSummary(sum.data);
      } catch { toast.error('Failed to load dashboard'); }
      finally { setLoading(false); }
    };
    load();
  }, []);

  useEffect(() => {
    if (!summary?.current_term_id) return;
    api.get('/dashboard/advanced/at-risk-students', {
      params: { term_id: summary.current_term_id, threshold: 40 },
    }).then(r => setAtRisk(r.data?.students || [])).catch(() => {});
    api.get('/dashboard/advanced/teacher-leaderboard', {
      params: { term_id: summary.current_term_id },
    }).then(r => setLeaderboard(r.data?.leaderboard || [])).catch(() => {});
  }, [summary?.current_term_id]);

  if (loading) return <div className="flex justify-center py-16"><div className="h-10 w-10 animate-spin rounded-full border-3 border-brand-600 border-t-transparent" /></div>;

  const tabs = [
    { key: 'summary' as const, label: 'Executive Summary', icon: Activity },
    { key: 'heatmap' as const, label: 'Performance Heatmap', icon: Target },
    { key: 'risk' as const, label: 'At-Risk Students', icon: AlertTriangle },
    { key: 'leaders' as const, label: 'Teacher Leaderboard', icon: Award },
  ];

  return (
    <div>
      <div className="page-header">
        <h2 className="text-2xl font-bold text-gray-900">Advanced Analytics</h2>
      </div>

      {/* Tabs */}
      <div className="mb-6 flex gap-1 rounded-lg bg-gray-100 p-1 w-fit">
        {tabs.map(t => (
          <button key={t.key} onClick={() => setActiveTab(t.key)}
            className={`flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-md transition-colors ${
              activeTab === t.key ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'
            }`}>
            <t.icon className="h-4 w-4" /> {t.label}
          </button>
        ))}
      </div>

      {/* Executive Summary */}
      {activeTab === 'summary' && summary && (
        <div className="space-y-6">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div className="stat-card">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-100">
                  <GraduationCap className="h-5 w-5 text-blue-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{summary.students?.total}</p>
                  <p className="text-xs text-gray-500">Students ({summary.students?.ratio})</p>
                </div>
              </div>
            </div>
            <div className="stat-card">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-purple-100">
                  <Users className="h-5 w-5 text-purple-600" />
                </div>
                <div><p className="text-2xl font-bold">{summary.teachers}</p><p className="text-xs text-gray-500">Teachers</p></div>
              </div>
            </div>
            <div className="stat-card">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-green-100">
                  <BookOpen className="h-5 w-5 text-green-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{summary.lessons_this_month?.rate || 0}%</p>
                  <p className="text-xs text-gray-500">Lesson Completion</p>
                </div>
              </div>
            </div>
            <div className="stat-card">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-amber-100">
                  <Target className="h-5 w-5 text-amber-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{summary.attendance_today?.rate || 0}%</p>
                  <p className="text-xs text-gray-500">Today's Attendance</p>
                </div>
              </div>
            </div>
          </div>

          {/* Attendance trend mini-chart */}
          {summary.attendance_trend && (
            <div className="card">
              <h3 className="text-lg font-semibold mb-4">7-Day Attendance Trend</h3>
              <div className="flex items-end gap-2 h-32">
                {summary.attendance_trend.map((d: any, i: number) => (
                  <div key={i} className="flex-1 flex flex-col items-center gap-1">
                    <span className="text-xs font-bold text-gray-700">{d.rate}%</span>
                    <div
                      className="w-full rounded-t-md transition-all"
                      style={{
                        height: `${d.rate}%`,
                        backgroundColor: d.rate >= 80 ? '#10b981' : d.rate >= 60 ? '#f59e0b' : '#ef4444',
                      }}
                    />
                    <span className="text-xs text-gray-400">{d.date?.slice(5)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Assessment & lesson stats */}
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="card">
              <h3 className="text-sm font-semibold text-gray-700 mb-2">This Week</h3>
              <p className="text-3xl font-bold text-brand-600">{summary.assessments_this_week}</p>
              <p className="text-xs text-gray-500">Assessments created</p>
            </div>
            <div className="card">
              <h3 className="text-sm font-semibold text-gray-700 mb-2">This Month</h3>
              <p className="text-3xl font-bold text-green-600">{summary.lessons_this_month?.completed || 0}</p>
              <p className="text-xs text-gray-500">Lessons completed of {summary.lessons_this_month?.total || 0}</p>
            </div>
          </div>
        </div>
      )}

      {/* Heatmap tab */}
      {activeTab === 'heatmap' && (
        <div className="card">
          <h3 className="text-lg font-semibold mb-4">Subject × Class Performance</h3>
          <p className="text-sm text-gray-400 mb-4">Select a term to load the performance heatmap.</p>
          <div className="text-center py-12 text-gray-300">
            <Target className="mx-auto h-16 w-16 mb-3" />
            <p>Heatmap data loads when a term is selected.</p>
            <p className="text-xs mt-2">API: GET /dashboard/advanced/performance-heatmap?term_id=UUID</p>
          </div>
        </div>
      )}

      {/* At-Risk Students */}
      {activeTab === 'risk' && (
        <div className="card">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-red-500" />
            At-Risk Students ({atRisk.length})
          </h3>
          {atRisk.length === 0 ? (
            <div className="text-center py-8 text-gray-400">
              <Award className="mx-auto h-10 w-10 mb-2 text-green-400" />
              <p>No at-risk students detected. Great job!</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead><tr className="border-b">
                  <th className="table-header">Student</th><th className="table-header">Admission #</th>
                  <th className="table-header">Mean %</th><th className="table-header">Attendance</th>
                  <th className="table-header">Risk Level</th><th className="table-header">Reasons</th>
                </tr></thead>
                <tbody>
                  {atRisk.map(s => (
                    <tr key={s.student_id} className="border-b border-gray-50 hover:bg-red-50">
                      <td className="table-cell font-medium">{s.name}</td>
                      <td className="table-cell font-mono text-xs">{s.admission_number}</td>
                      <td className="table-cell"><span className="font-bold text-red-600">{s.mean}%</span></td>
                      <td className="table-cell">{s.attendance_rate}%</td>
                      <td className="table-cell">
                        <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                          s.risk_level === 'high' ? 'bg-red-100 text-red-700' : 'bg-yellow-100 text-yellow-700'
                        }`}>{s.risk_level}</span>
                      </td>
                      <td className="table-cell text-xs text-gray-500">
                        {s.reasons?.join(' · ')}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Teacher Leaderboard */}
      {activeTab === 'leaders' && (
        <div className="card">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Award className="h-5 w-5 text-yellow-500" /> Teacher Leaderboard
          </h3>
          {leaderboard.length === 0 ? (
            <p className="text-gray-400 py-8 text-center">No data available for this term.</p>
          ) : (
            <div className="space-y-2">
              {leaderboard.map((t, i) => (
                <div key={t.teacher_id} className="flex items-center gap-4 p-3 rounded-lg border border-gray-100 hover:bg-gray-50">
                  <span className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
                    i === 0 ? 'bg-yellow-100 text-yellow-800' :
                    i === 1 ? 'bg-gray-200 text-gray-700' :
                    i === 2 ? 'bg-orange-100 text-orange-700' :
                    'bg-gray-100 text-gray-500'
                  }`}>{i + 1}</span>
                  <div className="flex-1">
                    <p className="font-medium text-sm">{t.name}</p>
                    <div className="flex gap-3 text-xs text-gray-400">
                      <span>Perf: {t.avg_performance}%</span>
                      <span>Lessons: {t.lesson_completion_rate}%</span>
                      <span>Students: {t.students_assessed}</span>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-lg font-bold text-brand-600">{t.composite_score}</p>
                    <p className="text-xs text-gray-400">composite</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
