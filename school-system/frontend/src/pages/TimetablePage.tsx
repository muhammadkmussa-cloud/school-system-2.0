import { useEffect, useState } from 'react';
import api from '@/services/api';
import type { Timetable } from '@/types';
import toast from 'react-hot-toast';
import { Calendar, Clock } from 'lucide-react';

const DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];

export default function TimetablePage() {
  const [timetables, setTimetables] = useState<Timetable[]>([]);
  const [selected, setSelected] = useState<Timetable | null>(null);
  const [loading, setLoading] = useState(true);
  const [subjectNames, setSubjectNames] = useState<Record<string, string>>({});
  const [classNames, setClassNames] = useState<Record<string, string>>({});

  useEffect(() => {
    (async () => {
      try {
        const [timetableRes, subjectRes, classRes] = await Promise.all([
          api.get<Timetable[]>('/timetable'),
          api.get<any[]>('/academic/subjects'),
          api.get<any[]>('/academic/classes'),
        ]);
        setTimetables(timetableRes.data);
        if (timetableRes.data.length > 0) setSelected(timetableRes.data[0]);
        const sMap: Record<string, string> = {};
        subjectRes.data.forEach((s: any) => { sMap[s.id] = s.name; });
        setSubjectNames(sMap);
        const cMap: Record<string, string> = {};
        classRes.data.forEach((c: any) => { cMap[c.id] = c.name; });
        setClassNames(cMap);
      } catch { toast.error('Failed to load timetables'); }
      finally { setLoading(false); }
    })();
  }, []);

  if (loading) return <div className="flex justify-center py-12"><div className="h-8 w-8 animate-spin rounded-full border-2 border-brand-600 border-t-transparent" /></div>;

  return (
    <div>
      <div className="page-header">
        <h2 className="text-2xl font-bold text-gray-900">Timetable</h2>
      </div>

      {timetables.length === 0 ? (
        <div className="card text-center py-12">
          <Calendar className="mx-auto h-12 w-12 text-gray-300 mb-4" />
          <p className="text-gray-500">No timetables created yet.</p>
        </div>
      ) : (
        <>
          {/* Selector */}
          <div className="mb-4 flex gap-2 flex-wrap">
            {timetables.map(t => (
              <button key={t.id}
                onClick={() => setSelected(t)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${selected?.id === t.id ? 'bg-brand-600 text-white' : 'bg-white border border-gray-200 text-gray-700 hover:bg-gray-50'}`}>
                {t.name}
              </button>
            ))}
          </div>

          {/* Grid */}
          {selected && (
            <div className="card overflow-x-auto">
              <div className="grid grid-cols-7 gap-2 min-w-[800px]">
                {DAYS.map((day, idx) => {
                  const entries = selected.entries.filter(e => e.day_of_week === idx);
                  return (
                    <div key={day} className="border border-gray-100 rounded-lg p-2 min-h-[200px]">
                      <p className="text-xs font-semibold text-gray-500 mb-2 text-center">{day.slice(0,3)}</p>
                      {entries.length === 0 ? (
                        <p className="text-xs text-gray-300 text-center mt-8">—</p>
                      ) : (
                        entries.map(e => (
                          <div key={e.id} className="mb-1 rounded bg-brand-50 p-1.5 text-xs">
                            <p className="font-medium text-brand-700 truncate">{subjectNames[e.subject_id] || e.subject_id?.slice(0,8)}</p>
                            <p className="text-brand-500 flex items-center gap-1"><Clock className="h-3 w-3" />{e.start_time?.slice(0,5)} - {e.end_time?.slice(0,5)}</p>
                            {e.room && <p className="text-gray-400">Room {e.room}</p>}
                          </div>
                        ))
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
