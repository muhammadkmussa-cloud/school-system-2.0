import { useEffect, useState } from 'react';
import api from '@/services/api';
import type { Student, AttendanceRecord } from '@/types';
import toast from 'react-hot-toast';
import { UserCheck, Search } from 'lucide-react';

const STATUS_OPTIONS = ['present', 'absent', 'late', 'excused'] as const;
type Status = (typeof STATUS_OPTIONS)[number];

export default function AttendancePage() {
  const [classes, setClasses] = useState<{ id: string; name: string }[]>([]);
  const [classId, setClassId] = useState('');
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10));
  const [students, setStudents] = useState<Student[]>([]);
  const [attendance, setAttendance] = useState<Record<string, Status>>({});
  const [remarks, setRemarks] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState<{ present: number; absent: number; late: number; excused: number; total: number; percentage: number } | null>(null);

  useEffect(() => {
    api.get('/academic/classes').then(({ data }) => setClasses(data)).catch(() => {});
  }, []);

  useEffect(() => {
    if (!classId) return;
    setLoading(true);
    Promise.all([
      api.get('/students', { params: { class_id: classId, status: 'active', page_size: 200 } }),
      api.get(`/attendance/class/${classId}`, { params: { attendance_date: date } }),
    ]).then(([sRes, aRes]) => {
      setStudents(sRes.data.items);
      const map: Record<string, Status> = {};
      const rMap: Record<string, string> = {};
      aRes.data.records.forEach((r: AttendanceRecord) => {
        map[r.student_id] = r.status as Status;
        if (r.remarks) rMap[r.student_id] = r.remarks;
      });
      setAttendance(map);
      setRemarks(rMap);
      setStats(aRes.data.stats);
    }).catch(() => toast.error('Failed to load attendance'))
    .finally(() => setLoading(false));
  }, [classId, date]);

  const submitAttendance = async () => {
    const records = students.map(s => ({
      student_id: s.id,
      status: attendance[s.id] || 'present',
      remarks: remarks[s.id] || null,
    }));
    try {
      await api.post('/attendance/batch', { class_id: classId, attendance_date: date, records });
      toast.success('Attendance recorded!');
      // Refresh
      const { data } = await api.get(`/attendance/class/${classId}`, { params: { attendance_date: date } });
      setStats(data.stats);
    } catch { toast.error('Failed to save attendance'); }
  };

  return (
    <div>
      <div className="page-header">
        <h2 className="text-2xl font-bold text-gray-900">Attendance</h2>
      </div>

      {/* Controls */}
      <div className="card mb-6">
        <div className="flex flex-wrap gap-4 items-end">
          <div className="flex-1 min-w-[200px]">
            <label className="label">Class</label>
            <select className="input-field" value={classId} onChange={e => setClassId(e.target.value)}>
              <option value="">Select a class…</option>
              {classes.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </div>
          <div>
            <label className="label">Date</label>
            <input type="date" className="input-field" value={date} onChange={e => setDate(e.target.value)} />
          </div>
        </div>

        {/* Stats bar */}
        {stats && (
          <div className="mt-4 grid grid-cols-5 gap-2 text-center">
            {(['present','absent','late','excused'] as const).map(s => (
              <div key={s} className={`rounded-lg p-2 ${s==='present'?'bg-green-50':s==='absent'?'bg-red-50':s==='late'?'bg-yellow-50':'bg-blue-50'}`}>
                <p className="text-lg font-bold">{stats[s]}</p>
                <p className="text-xs capitalize text-gray-500">{s}</p>
              </div>
            ))}
            <div className="rounded-lg bg-gray-50 p-2">
              <p className="text-lg font-bold">{stats.percentage}%</p>
              <p className="text-xs text-gray-500">Rate</p>
            </div>
          </div>
        )}
      </div>

      {/* Student list */}
      {classId && !loading && (
        <div className="card">
          <div className="space-y-1">
            {students.map(s => (
              <div key={s.id} className="flex items-center gap-3 rounded-lg border border-gray-100 p-3 hover:bg-gray-50">
                <span className="text-sm font-medium w-8">{s.admission_number}</span>
                <span className="flex-1 text-sm">{s.full_name}</span>
                <select
                  className="input-field w-28 text-xs"
                  value={attendance[s.id] || 'present'}
                  onChange={e => setAttendance({...attendance, [s.id]: e.target.value as Status})}
                >
                  {STATUS_OPTIONS.map(st => <option key={st} value={st}>{st}</option>)}
                </select>
                <input
                  className="input-field w-32 text-xs"
                  placeholder="Remarks"
                  value={remarks[s.id] || ''}
                  onChange={e => setRemarks({...remarks, [s.id]: e.target.value})}
                />
              </div>
            ))}
          </div>
          <button onClick={submitAttendance} className="btn-primary mt-4 w-full sm:w-auto">
            <UserCheck className="h-4 w-4 mr-2" />
            Save Attendance
          </button>
        </div>
      )}
    </div>
  );
}
