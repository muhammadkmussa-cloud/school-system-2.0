import { useEffect, useState } from 'react';
import api from '@/services/api';
import toast from 'react-hot-toast';
import { ArrowRight, RotateCcw, Users, AlertTriangle, GraduationCap } from 'lucide-react';
import type { Class, AcademicYear } from '@/types';

export default function PromotionManager() {
  const [classes, setClasses] = useState<Class[]>([]);
  const [years, setYears] = useState<AcademicYear[]>([]);
  const [sourceClass, setSourceClass] = useState('');
  const [targetClass, setTargetClass] = useState('');
  const [targetYear, setTargetYear] = useState('');
  const [minMean, setMinMean] = useState('');
  const [path, setPath] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);

  useEffect(() => {
    Promise.all([
      api.get('/academic/classes'),
      api.get('/academic/years'),
    ]).then(([c, y]) => {
      setClasses(c.data);
      setYears(y.data.filter((yr: AcademicYear) => yr.is_current));
    });
  }, []);

  useEffect(() => {
    if (sourceClass) {
      api.get(`/promotion/path/${sourceClass}`).then(({ data }) => setPath(data.chain));
    }
  }, [sourceClass]);

  const handlePromote = async () => {
    if (!sourceClass || !targetClass || !targetYear) {
      toast.error('Please select source, target class, and academic year');
      return;
    }
    setLoading(true);
    try {
      const { data } = await api.post(`/promotion/class/${sourceClass}`, null, {
        params: {
          target_class_id: targetClass,
          target_academic_year_id: targetYear,
          min_mean: minMean || undefined,
        },
      });
      setResult(data);
      if (data.promoted > 0) toast.success(`${data.promoted} students promoted!`);
      if (data.retained > 0) toast(`${data.retained} students retained`, { icon: '⚠️' });
    } catch (err: any) { toast.error(err.response?.data?.detail || 'Promotion failed'); }
    finally { setLoading(false); }
  };

  const handleRollback = async () => {
    try {
      const { data } = await api.post('/promotion/rollback');
      toast.success(`${data.restored} students restored`);
      setResult(null);
    } catch { toast.error('Rollback failed'); }
  };

  return (
    <div>
      <div className="page-header">
        <h2 className="text-2xl font-bold text-gray-900">Student Promotion</h2>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Promotion controls */}
        <div className="card">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <GraduationCap className="h-5 w-5 text-brand-600" /> Promote Class
          </h3>

          <div className="space-y-4">
            <div>
              <label className="label">Source Class</label>
              <select className="input-field" value={sourceClass} onChange={e => setSourceClass(e.target.value)}>
                <option value="">Select class…</option>
                {classes.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </div>

            {path.length > 0 && (
              <div className="flex items-center gap-2 text-sm text-gray-500 bg-gray-50 rounded-lg p-3">
                <span>Path:</span>
                {path.map((p, i) => (
                  <span key={p.id} className="flex items-center gap-1">
                    <span className={p.is_current ? 'font-bold text-brand-600' : ''}>{p.name}</span>
                    {i < path.length - 1 && <ArrowRight className="h-3 w-3" />}
                  </span>
                ))}
              </div>
            )}

            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label className="label">Target Class</label>
                <select className="input-field" value={targetClass} onChange={e => setTargetClass(e.target.value)}>
                  <option value="">Select…</option>
                  {classes.filter(c => c.id !== sourceClass).map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                </select>
              </div>
              <div>
                <label className="label">Target Academic Year</label>
                <select className="input-field" value={targetYear} onChange={e => setTargetYear(e.target.value)}>
                  <option value="">Select…</option>
                  {years.map(y => <option key={y.id} value={y.id}>{y.name}</option>)}
                </select>
              </div>
            </div>

            <div>
              <label className="label">Minimum Mean (optional)</label>
              <input type="number" className="input-field w-32" placeholder="e.g. 35" value={minMean} onChange={e => setMinMean(e.target.value)} />
              <p className="text-xs text-gray-400 mt-1">Students below this mean will be retained.</p>
            </div>

            <div className="flex gap-3">
              <button onClick={handlePromote} disabled={loading} className="btn-primary gap-2">
                <Users className="h-4 w-4" /> {loading ? 'Promoting…' : 'Promote Students'}
              </button>
              {result && (
                <button onClick={handleRollback} className="btn-danger gap-2">
                  <RotateCcw className="h-4 w-4" /> Rollback
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Results */}
        {result && (
          <div className="card">
            <h3 className="text-lg font-semibold mb-4">Promotion Results</h3>
            <div className="grid grid-cols-3 gap-4 mb-4">
              <div className="text-center p-4 bg-green-50 rounded-lg">
                <p className="text-3xl font-bold text-green-700">{result.promoted}</p>
                <p className="text-xs text-green-600">Promoted</p>
              </div>
              <div className="text-center p-4 bg-yellow-50 rounded-lg">
                <p className="text-3xl font-bold text-yellow-700">{result.retained}</p>
                <p className="text-xs text-yellow-600">Retained</p>
              </div>
              <div className="text-center p-4 bg-blue-50 rounded-lg">
                <p className="text-3xl font-bold text-blue-700">{result.graduated || 0}</p>
                <p className="text-xs text-blue-600">Graduated</p>
              </div>
            </div>
            {result.errors?.length > 0 && (
              <div className="bg-red-50 rounded-lg p-3">
                {result.errors.map((e: string, i: number) => (
                  <p key={i} className="text-sm text-red-600 flex items-center gap-1">
                    <AlertTriangle className="h-3 w-3" /> {e}
                  </p>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
