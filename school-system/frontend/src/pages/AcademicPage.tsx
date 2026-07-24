import { useEffect, useState } from 'react';
import api from '@/services/api';
import toast from 'react-hot-toast';
import { Plus } from 'lucide-react';
import type { AcademicYear, Term, Class, Stream, Subject, Department } from '@/types';

type Tab = 'years' | 'terms' | 'classes' | 'streams' | 'subjects' | 'departments';

export default function AcademicPage() {
  const [tab, setTab] = useState<Tab>('years');
  const [years, setYears] = useState<AcademicYear[]>([]);
  const [terms, setTerms] = useState<Term[]>([]);
  const [classes, setClasses] = useState<Class[]>([]);
  const [streams, setStreams] = useState<Stream[]>([]);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [loading, setLoading] = useState(true);

  const tabs: { key: Tab; label: string }[] = [
    { key: 'years', label: 'Academic Years' },
    { key: 'terms', label: 'Terms' },
    { key: 'classes', label: 'Classes' },
    { key: 'streams', label: 'Streams' },
    { key: 'subjects', label: 'Subjects' },
    { key: 'departments', label: 'Departments' },
  ];

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        const [y, t, c, s, sub, d] = await Promise.all([
          api.get('/academic/years'),
          api.get('/academic/terms'),
          api.get('/academic/classes'),
          api.get('/academic/streams'),
          api.get('/academic/subjects'),
          api.get('/academic/departments'),
        ]);
        setYears(y.data);
        setTerms(t.data);
        setClasses(c.data);
        setStreams(s.data);
        setSubjects(sub.data);
        setDepartments(d.data);
      } catch { toast.error('Failed to load academic data'); }
      finally { setLoading(false); }
    };
    fetchData();
  }, []);

  if (loading) return <div className="flex justify-center py-12"><div className="h-8 w-8 animate-spin rounded-full border-2 border-brand-600 border-t-transparent" /></div>;

  return (
    <div>
      <div className="page-header">
        <h2 className="text-2xl font-bold text-gray-900">Academic Structure</h2>
      </div>

      {/* Tabs */}
      <div className="mb-6 flex gap-1 rounded-lg bg-gray-100 p-1 w-fit">
        {tabs.map(t => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${tab === t.key ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'}`}>
            {t.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="card">
        {tab === 'years' && (
          <div>
            <h3 className="text-lg font-semibold mb-4">Academic Years</h3>
            <div className="space-y-2">
              {years.map(y => (
                <div key={y.id} className="flex items-center justify-between rounded-lg border border-gray-100 p-3">
                  <div><p className="font-medium">{y.name}</p><p className="text-xs text-gray-500">{y.start_date} → {y.end_date}</p></div>
                  {y.is_current && <span className="rounded-full bg-green-100 px-2 py-0.5 text-xs text-green-700">Current</span>}
                </div>
              ))}
            </div>
          </div>
        )}

        {tab === 'terms' && (
          <div>
            <h3 className="text-lg font-semibold mb-4">Terms</h3>
            <div className="space-y-2">
              {terms.map(t => (
                <div key={t.id} className="flex items-center justify-between rounded-lg border border-gray-100 p-3">
                  <div><p className="font-medium">{t.name} (Term {t.term_number})</p><p className="text-xs text-gray-500">{t.start_date} → {t.end_date}</p></div>
                  {t.is_current && <span className="rounded-full bg-green-100 px-2 py-0.5 text-xs text-green-700">Current</span>}
                </div>
              ))}
            </div>
          </div>
        )}

        {tab === 'classes' && (
          <div>
            <h3 className="text-lg font-semibold mb-4">Classes</h3>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {classes.map(c => (
                <div key={c.id} className="rounded-lg border border-gray-200 p-4">
                  <p className="font-semibold text-gray-900">{c.name}</p>
                  {c.level && <p className="text-xs text-gray-500">Level {c.level}</p>}
                  {c.description && <p className="text-xs text-gray-400 mt-1">{c.description}</p>}
                </div>
              ))}
            </div>
          </div>
        )}

        {tab === 'streams' && (
          <div>
            <h3 className="text-lg font-semibold mb-4">Streams</h3>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {streams.map(s => (
                <div key={s.id} className="rounded-lg border border-gray-200 p-4">
                  <p className="font-semibold text-gray-900">{s.name}</p>
                  <p className="text-xs text-gray-500">Class: {s.class_id?.slice(0,8)}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {tab === 'subjects' && (
          <div>
            <h3 className="text-lg font-semibold mb-4">Subjects</h3>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {subjects.map(s => (
                <div key={s.id} className="rounded-lg border border-gray-200 p-4">
                  <p className="font-semibold text-gray-900">{s.name}</p>
                  <p className="text-xs text-gray-500 font-mono">{s.code}</p>
                  {s.description && <p className="text-xs text-gray-400 mt-1">{s.description}</p>}
                </div>
              ))}
            </div>
          </div>
        )}

        {tab === 'departments' && (
          <div>
            <h3 className="text-lg font-semibold mb-4">Departments</h3>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {departments.map(d => (
                <div key={d.id} className="rounded-lg border border-gray-200 p-4">
                  <p className="font-semibold text-gray-900">{d.name}</p>
                  {d.description && <p className="text-xs text-gray-400 mt-1">{d.description}</p>}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
