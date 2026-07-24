import { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '@/services/api';
import toast from 'react-hot-toast';
import {
  Check, ChevronRight, ChevronLeft, School, BookOpen, Users,
  UserPlus, Upload, Download, Printer, AlertTriangle, X,
} from 'lucide-react';
import clsx from 'clsx';

interface TeacherCredential {
  id: string;
  employee_number: string;
  full_name: string;
  email: string;
  temp_password: string;
  is_active: boolean;
}

interface ValidationError {
  row: number;
  field: string;
  message: string;
}

type StepId = 'school' | 'academic' | 'staff';

export default function SetupWizard() {
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [step, setStep] = useState<StepId>('school');
  const [loading, setLoading] = useState(false);
  const [completed, setCompleted] = useState<string[]>([]);

  // ── Step 1: School Information ───────────────────────────────────
  const [schoolInfo, setSchoolInfo] = useState({
    name: '', code: '', school_type: 'secondary', curriculum: 'kicd',
    country: 'Kenya', county: '', address: '', email: '', phone: '',
    timezone: 'Africa/Nairobi',
    academic_year_name: '2026 Academic Year',
    academic_year_start: '2026-01-05', academic_year_end: '2026-12-18',
  });

  // ── Step 2: Academic Structure ───────────────────────────────────
  const [grades, setGrades] = useState([
    { name: 'Form 1', level: 1, num_streams: 2 },
    { name: 'Form 2', level: 2, num_streams: 2 },
    { name: 'Form 3', level: 3, num_streams: 2 },
    { name: 'Form 4', level: 4, num_streams: 2 },
  ]);
  const [subjects, setSubjects] = useState([
    { code: 'MAT', name: 'Mathematics', is_elective: false },
    { code: 'ENG', name: 'English', is_elective: false },
    { code: 'KIS', name: 'Kiswahili', is_elective: false },
    { code: 'BIO', name: 'Biology', is_elective: false },
    { code: 'PHY', name: 'Physics', is_elective: true },
    { code: 'CHE', name: 'Chemistry', is_elective: false },
    { code: 'HIS', name: 'History', is_elective: true },
    { code: 'GEO', name: 'Geography', is_elective: true },
    { code: 'CRE', name: 'CRE', is_elective: true },
    { code: 'BUS', name: 'Business Studies', is_elective: true },
    { code: 'AGR', name: 'Agriculture', is_elective: true },
    { code: 'COM', name: 'Computer Studies', is_elective: true },
  ]);
  const [termNames] = useState(['Term 1', 'Term 2', 'Term 3']);
  const [gradingSystem, setGradingSystem] = useState('a-f');
  const [newSubject, setNewSubject] = useState({ code: '', name: '' });

  // ── Step 3: Staff Setup ──────────────────────────────────────────
  const [staffMode, setStaffMode] = useState<'manual' | 'import' | ''>('');
  const [manualStaff, setManualStaff] = useState([{ full_name: '', email: '', phone: '', employee_number: '' }]);

  // Import state
  const [importFile, setImportFile] = useState<File | null>(null);
  const [importErrors, setImportErrors] = useState<ValidationError[]>([]);
  const [importPreview, setImportPreview] = useState<any[]>([]);
  const [importValid, setImportValid] = useState(false);
  const [importing, setImporting] = useState(false);

  // Credentials result
  const [credentials, setCredentials] = useState<TeacherCredential[]>([]);
  const [showCredentials, setShowCredentials] = useState(false);

  // ── Handlers ─────────────────────────────────────────────────────

  const handleStep1 = async () => {
    setLoading(true);
    try {
      await api.post('/onboarding/setup/step-1', {
        ...schoolInfo,
        email: schoolInfo.email || undefined,
        phone: schoolInfo.phone || undefined,
        address: schoolInfo.address || undefined,
        academic_year_start: schoolInfo.academic_year_start,
        academic_year_end: schoolInfo.academic_year_end,
      });
      toast.success('School information saved!');
      setCompleted(prev => [...prev, 'school']);
      setStep('academic');
    } catch (err: any) { toast.error(err.response?.data?.detail || 'Failed'); }
    finally { setLoading(false); }
  };

  const handleStep2 = async () => {
    setLoading(true);
    try {
      await api.post('/onboarding/setup/step-2', {
        grades: grades.map(g => ({ name: g.name, level: g.level, num_streams: g.num_streams })),
        subjects: subjects.filter(s => s.code && s.name).map(s => ({ code: s.code, name: s.name, is_elective: s.is_elective })),
        term_names: termNames,
        grading_system: gradingSystem,
      });
      toast.success('Academic structure created!');
      setCompleted(prev => [...prev, 'academic']);
      setStep('staff');
    } catch (err: any) { toast.error(err.response?.data?.detail || 'Failed'); }
    finally { setLoading(false); }
  };

  const handleManualProvision = async () => {
    const valid = manualStaff.filter(s => s.full_name && s.email);
    if (valid.length === 0) return toast.error('Enter at least one teacher');
    setLoading(true);
    try {
      const { data } = await api.post('/onboarding/setup/step-3/manual', {
        staff_list: valid.map(s => ({
          full_name: s.full_name,
          email: s.email,
          phone: s.phone || undefined,
          employee_number: s.employee_number || undefined,
        })),
      });
      setCredentials(data.teachers);
      setShowCredentials(true);
      setCompleted(prev => [...prev, 'staff']);
      toast.success(`${data.total_created} teacher accounts provisioned!`);
    } catch (err: any) { toast.error(err.response?.data?.detail || 'Failed'); }
    finally { setLoading(false); }
  };

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setImportFile(file);
    const reader = new FileReader();
    reader.onload = async (ev) => {
      const base64 = (ev.target?.result as string)?.split(',')[1];
      if (!base64) return toast.error('Could not read file');
      try {
        const { data } = await api.post('/onboarding/setup/step-3/validate', {
          file_content: base64, filename: file.name,
        });
        setImportErrors(data.errors || []);
        setImportPreview(data.preview || []);
        setImportValid(data.valid);
      } catch (err: any) { toast.error(err.response?.data?.detail || 'Validation failed'); }
    };
    reader.readAsDataURL(file);
  };

  const handleConfirmImport = async () => {
    if (!importFile) return;
    setImporting(true);
    const reader = new FileReader();
    reader.onload = async (ev) => {
      const base64 = (ev.target?.result as string)?.split(',')[1];
      if (!base64) { setImporting(false); return; }
      try {
        const { data } = await api.post('/onboarding/setup/step-3/confirm', {
          file_content: base64, filename: importFile.name,
        });
        setCredentials(data.teachers);
        setShowCredentials(true);
        setCompleted(prev => [...prev, 'staff']);
        toast.success(`${data.total_created} teachers imported!`);
      } catch (err: any) { toast.error(err.response?.data?.detail || 'Import failed'); }
      finally { setImporting(false); }
    };
    reader.readAsDataURL(importFile);
  };

  const handleFinish = () => {
    toast.success('School setup complete!');
    setTimeout(() => navigate('/'), 1000);
  };

  const handlePrintCredentials = () => {
    if (credentials.length === 0) return;
    const rows = credentials.map(t => `
      <tr><td style="border:1px solid #ccc;padding:6px 10px;font-family:monospace">${t.employee_number}</td>
      <td style="border:1px solid #ccc;padding:6px 10px">${t.full_name}</td>
      <td style="border:1px solid #ccc;padding:6px 10px;font-family:monospace">${t.email}</td>
      <td style="border:1px solid #ccc;padding:6px 10px;font-family:monospace">${t.temp_password}</td>
      <td style="border:1px solid #ccc;padding:6px 10px">Pending</td></tr>
    `).join('');
    const w = window.open('', '_blank');
    if (!w) return;
    w.document.write(`<html><head><title>Staff Credentials</title><style>
body{font-family:Arial,sans-serif;padding:40px;max-width:900px;margin:auto}
h1{font-size:20px;margin-bottom:4px}table{width:100%;border-collapse:collapse}
th{background:#f5f5f5;border:1px solid #ccc;padding:8px 10px;text-align:left;font-size:11px;text-transform:uppercase}
td{border:1px solid #ccc;padding:6px 10px;font-size:12px}
.warn{background:#fff3cd;padding:10px;border-radius:4px;margin:20px 0;font-size:12px}
</style></head><body><h1>School Management System — Staff Credentials</h1>
<p style="color:#666">Generated: ${new Date().toLocaleString()}</p>
<div class="warn">⚠ Temporary passwords — teachers must change on first login.</div>
<table><thead><tr><th>Employee #</th><th>Name</th><th>Username</th><th>Temp Password</th><th>Status</th></tr></thead><tbody>${rows}</tbody></table></body></html>`);
    w.document.close();
    w.print();
  };

  // ── Progress ─────────────────────────────────────────────────────

  const steps = [
    { id: 'school' as const, title: 'School Information', desc: 'Basic school details & academic year', icon: School },
    { id: 'academic' as const, title: 'Academic Structure', desc: 'Classes, streams, subjects & terms', icon: BookOpen },
    { id: 'staff' as const, title: 'Staff Setup', desc: 'Provision teacher accounts', icon: Users },
  ];

  const progress = steps.findIndex(s => s.id === step);
  const isComplete = completed.length === 3;

  return (
    <div className="min-h-[80vh] flex items-center justify-center px-4">
      <div className="w-full max-w-4xl">
        {/* Progress stepper */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-4">
            {steps.map((s, i) => (
              <div key={s.id} className="flex flex-col items-center">
                <div className={clsx(
                  'flex h-10 w-10 items-center justify-center rounded-full text-sm font-bold transition-all',
                  completed.includes(s.id) ? 'bg-green-500 text-white' :
                  step === s.id ? 'bg-brand-600 text-white ring-4 ring-brand-100' :
                  'bg-gray-200 text-gray-400'
                )}>
                  {completed.includes(s.id) ? <Check className="h-5 w-5" /> : i + 1}
                </div>
                <span className={clsx('mt-1.5 text-xs font-medium hidden sm:block',
                  step === s.id ? 'text-brand-700' : 'text-gray-500')}>{s.title}</span>
              </div>
            ))}
          </div>
          <div className="h-2 bg-gray-200 rounded-full">
            <div className="h-2 bg-brand-600 rounded-full transition-all" style={{ width: `${(progress / 2) * 100}%` }} />
          </div>
        </div>

        {/* ──────────────────── STEP 1: SCHOOL INFO ──────────────────── */}
        {step === 'school' && (
          <div className="card">
            <div className="flex items-center gap-3 mb-6">
              <School className="h-6 w-6 text-brand-600" />
              <div>
                <h2 className="text-xl font-bold">School Information</h2>
                <p className="text-sm text-gray-500">Tell us about your school</p>
              </div>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div><label className="label">School Name *</label><input className="input-field" value={schoolInfo.name} onChange={e => setSchoolInfo({...schoolInfo, name: e.target.value})} /></div>
              <div><label className="label">School Code *</label><input className="input-field" value={schoolInfo.code} onChange={e => setSchoolInfo({...schoolInfo, code: e.target.value})} /></div>
              <div><label className="label">School Type</label>
                <select className="input-field" value={schoolInfo.school_type} onChange={e => setSchoolInfo({...schoolInfo, school_type: e.target.value})}>
                  <option value="primary">Primary</option><option value="secondary">Secondary</option><option value="both">Both</option>
                </select>
              </div>
              <div><label className="label">Curriculum</label>
                <select className="input-field" value={schoolInfo.curriculum} onChange={e => setSchoolInfo({...schoolInfo, curriculum: e.target.value})}>
                  <option value="kicd">KICD (CBC)</option><option value="igcse">IGCSE</option><option value="ib">IB</option><option value="other">Other</option>
                </select>
              </div>
              <div><label className="label">Country</label>
                <select className="input-field" value={schoolInfo.country} onChange={e => setSchoolInfo({...schoolInfo, country: e.target.value})}>
                  <option value="Kenya">Kenya</option><option value="Uganda">Uganda</option><option value="Tanzania">Tanzania</option><option value="Rwanda">Rwanda</option>
                </select>
              </div>
              <div><label className="label">County / Region</label><input className="input-field" value={schoolInfo.county} onChange={e => setSchoolInfo({...schoolInfo, county: e.target.value})} /></div>
              <div className="sm:col-span-2"><label className="label">Address</label><input className="input-field" value={schoolInfo.address} onChange={e => setSchoolInfo({...schoolInfo, address: e.target.value})} /></div>
              <div><label className="label">Email</label><input type="email" className="input-field" value={schoolInfo.email} onChange={e => setSchoolInfo({...schoolInfo, email: e.target.value})} /></div>
              <div><label className="label">Phone</label><input className="input-field" value={schoolInfo.phone} onChange={e => setSchoolInfo({...schoolInfo, phone: e.target.value})} /></div>
              <div><label className="label">Timezone</label>
                <select className="input-field" value={schoolInfo.timezone} onChange={e => setSchoolInfo({...schoolInfo, timezone: e.target.value})}>
                  <option value="Africa/Nairobi">Africa/Nairobi (UTC+3)</option>
                  <option value="Africa/Kampala">Africa/Kampala (UTC+3)</option>
                  <option value="Africa/Dar_es_Salaam">Africa/Dar es Salaam (UTC+3)</option>
                  <option value="Africa/Kigali">Africa/Kigali (UTC+2)</option>
                </select>
              </div>
              <div className="sm:col-span-2 border-t pt-4 mt-2">
                <h3 className="text-sm font-semibold text-gray-700 mb-3">Academic Year</h3>
                <div className="grid gap-4 sm:grid-cols-3">
                  <div className="sm:col-span-3"><label className="label">Year Name</label><input className="input-field" value={schoolInfo.academic_year_name} onChange={e => setSchoolInfo({...schoolInfo, academic_year_name: e.target.value})} /></div>
                  <div><label className="label">Start Date</label><input type="date" className="input-field" value={schoolInfo.academic_year_start} onChange={e => setSchoolInfo({...schoolInfo, academic_year_start: e.target.value})} /></div>
                  <div><label className="label">End Date</label><input type="date" className="input-field" value={schoolInfo.academic_year_end} onChange={e => setSchoolInfo({...schoolInfo, academic_year_end: e.target.value})} /></div>
                </div>
              </div>
            </div>
            <button onClick={handleStep1} disabled={loading || !schoolInfo.name || !schoolInfo.code}
              className="btn-primary w-full mt-6">
              {loading ? 'Saving…' : 'Save & Continue'} <ChevronRight className="h-4 w-4 inline" />
            </button>
          </div>
        )}

        {/* ──────────────────── STEP 2: ACADEMIC STRUCTURE ────────────── */}
        {step === 'academic' && (
          <div className="card">
            <div className="flex items-center gap-3 mb-6">
              <BookOpen className="h-6 w-6 text-brand-600" />
              <div>
                <h2 className="text-xl font-bold">Academic Structure</h2>
                <p className="text-sm text-gray-500">Configure classes, streams, subjects & terms</p>
              </div>
            </div>

            <div className="space-y-6">
              {/* Grades */}
              <div>
                <h3 className="text-sm font-semibold text-gray-700 mb-3">Grades / Forms</h3>
                <div className="space-y-2">
                  {grades.map((g, i) => (
                    <div key={i} className="flex gap-3 items-end">
                      <div className="flex-1"><input className="input-field" placeholder="Name (e.g. Form 1)" value={g.name} onChange={e => { const ng = [...grades]; ng[i].name = e.target.value; setGrades(ng); }} /></div>
                      <div className="w-20"><input type="number" className="input-field" placeholder="Level" value={g.level} onChange={e => { const ng = [...grades]; ng[i].level = parseInt(e.target.value) || 0; setGrades(ng); }} /></div>
                      <div className="w-36"><label className="text-xs text-gray-500 block mb-0.5">Streams</label>
                        <select className="input-field" value={g.num_streams} onChange={e => { const ng = [...grades]; ng[i].num_streams = parseInt(e.target.value) || 2; setGrades(ng); }}>
                          {[1,2,3,4,5,6,7,8].map(n => <option key={n} value={n}>{n}</option>)}
                        </select>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Subjects */}
              <div>
                <h3 className="text-sm font-semibold text-gray-700 mb-3">Subjects</h3>
                <div className="flex flex-wrap gap-2 mb-3">
                  {subjects.map((s, i) => (
                    <span key={i} className={clsx('inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium',
                      s.is_elective ? 'bg-purple-100 text-purple-700' : 'bg-blue-100 text-blue-700')}>
                      {s.code}
                      <button onClick={() => setSubjects(subjects.filter((_, j) => j !== i))} className="hover:text-red-500">&times;</button>
                    </span>
                  ))}
                </div>
                <div className="flex gap-2">
                  <input className="input-field w-20" placeholder="Code" value={newSubject.code} onChange={e => setNewSubject({...newSubject, code: e.target.value})} />
                  <input className="input-field flex-1" placeholder="Subject name" value={newSubject.name} onChange={e => setNewSubject({...newSubject, name: e.target.value})} />
                  <button onClick={() => {
                    if (newSubject.code && newSubject.name) {
                      setSubjects([...subjects, { ...newSubject, is_elective: false }]);
                      setNewSubject({ code: '', name: '' });
                    }
                  }} className="btn-secondary text-sm">Add</button>
                </div>
              </div>

              {/* Terms & Grading */}
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <h3 className="text-sm font-semibold text-gray-700 mb-2">Terms</h3>
                  <p className="text-xs text-gray-500">3 terms will be created: {termNames.join(', ')}</p>
                </div>
                <div>
                  <label className="label">Grading System</label>
                  <select className="input-field" value={gradingSystem} onChange={e => setGradingSystem(e.target.value)}>
                    <option value="a-f">A-F (A=80-100, B=70-79, C=60-69, D=50-59, E=40-49, F=&lt;40)</option>
                    <option value="percentage">Percentage (0-100%)</option>
                    <option value="both">Both (Letter + Percentage)</option>
                  </select>
                </div>
              </div>
            </div>

            <div className="flex gap-3 mt-6">
              <button onClick={() => setStep('school')} className="btn-secondary gap-1"><ChevronLeft className="h-4 w-4" /> Back</button>
              <button onClick={handleStep2} disabled={loading} className="btn-primary flex-1">
                {loading ? 'Creating…' : 'Create Structure & Continue'} <ChevronRight className="h-4 w-4 inline" />
              </button>
            </div>
          </div>
        )}

        {/* ──────────────────── STEP 3: STAFF SETUP ───────────────────── */}
        {step === 'staff' && (
          <div className="card">
            <div className="flex items-center gap-3 mb-6">
              <Users className="h-6 w-6 text-brand-600" />
              <div>
                <h2 className="text-xl font-bold">Staff Setup</h2>
                <p className="text-sm text-gray-500">Provision teacher accounts for your school</p>
              </div>
            </div>

            {!staffMode ? (
              <div className="grid gap-4 sm:grid-cols-2">
                <button onClick={() => setStaffMode('manual')}
                  className="rounded-xl border-2 border-dashed border-gray-300 p-8 text-center hover:border-brand-400 hover:bg-brand-50 transition-all">
                  <UserPlus className="mx-auto h-10 w-10 text-brand-500 mb-3" />
                  <h3 className="font-semibold text-gray-900">Manual Entry</h3>
                  <p className="text-sm text-gray-500 mt-1">Enter teacher details one by one</p>
                </button>
                <button onClick={() => setStaffMode('import')}
                  className="rounded-xl border-2 border-dashed border-gray-300 p-8 text-center hover:border-brand-400 hover:bg-brand-50 transition-all">
                  <Upload className="mx-auto h-10 w-10 text-brand-500 mb-3" />
                  <h3 className="font-semibold text-gray-900">Bulk Import</h3>
                  <p className="text-sm text-gray-500 mt-1">Upload CSV or Excel file</p>
                </button>
              </div>
            ) : staffMode === 'manual' ? (
              <div className="space-y-4">
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-sm text-blue-800">
                  Enter teacher details below. Each teacher will get an auto-generated account with temporary credentials.
                </div>
                {manualStaff.map((s, i) => (
                  <div key={i} className="grid gap-3 sm:grid-cols-4 p-3 bg-gray-50 rounded-lg">
                    <input className="input-field" placeholder="Full Name *" value={s.full_name}
                      onChange={e => { const ns = [...manualStaff]; ns[i].full_name = e.target.value; setManualStaff(ns); }} />
                    <input className="input-field" placeholder="Email *" type="email" value={s.email}
                      onChange={e => { const ns = [...manualStaff]; ns[i].email = e.target.value; setManualStaff(ns); }} />
                    <input className="input-field" placeholder="Phone" value={s.phone}
                      onChange={e => { const ns = [...manualStaff]; ns[i].phone = e.target.value; setManualStaff(ns); }} />
                    <div className="flex gap-1">
                      <input className="input-field flex-1" placeholder="Employee #" value={s.employee_number}
                        onChange={e => { const ns = [...manualStaff]; ns[i].employee_number = e.target.value; setManualStaff(ns); }} />
                      {manualStaff.length > 1 && (
                        <button onClick={() => setManualStaff(manualStaff.filter((_, j) => j !== i))}
                          className="p-2 text-red-400 hover:text-red-600"><X className="h-4 w-4" /></button>
                      )}
                    </div>
                  </div>
                ))}
                <button onClick={() => setManualStaff([...manualStaff, { full_name: '', email: '', phone: '', employee_number: '' }])}
                  className="text-sm text-brand-600 hover:underline">+ Add another teacher</button>
                <div className="flex gap-3 pt-2">
                  <button onClick={() => setStaffMode('')} className="btn-secondary gap-1"><ChevronLeft className="h-4 w-4" /> Back</button>
                  <button onClick={handleManualProvision} disabled={loading}
                    className="btn-primary flex-1 gap-2">
                    {loading ? 'Provisioning…' : <><UserPlus className="h-4 w-4" /> Provision {manualStaff.filter(s => s.full_name && s.email).length} Teacher(s)</>}
                  </button>
                </div>
              </div>
            ) : (
              /* Bulk Import */
              <div className="space-y-4">
                <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center hover:border-brand-400 transition-colors">
                  <Upload className="mx-auto h-10 w-10 text-gray-400 mb-3" />
                  <p className="text-sm text-gray-500 mb-1">Upload CSV or Excel (.xlsx) file</p>
                  <a href="/api/v1/onboarding/setup/staff-template"
                    className="text-sm text-brand-600 hover:underline mb-3 inline-block">Download template</a>
                  <div className="mt-2">
                    <button onClick={() => fileInputRef.current?.click()} className="btn-secondary">Choose File</button>
                    <input ref={fileInputRef} type="file" accept=".csv,.xlsx" className="hidden" onChange={handleFileSelect} />
                  </div>
                  {importFile && <p className="text-sm text-gray-600 mt-2">{importFile.name}</p>}
                </div>

                {importErrors.length > 0 && (
                  <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                    <p className="text-sm font-medium text-red-800 flex items-center gap-2 mb-2">
                      <AlertTriangle className="h-4 w-4" /> {importErrors.length} error(s)
                    </p>
                    <ul className="text-xs text-red-700 space-y-1 max-h-32 overflow-y-auto">
                      {importErrors.map((e, i) => (
                        <li key={i}>Row {e.row}: <strong>{e.field}</strong> — {e.message}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {importPreview.length > 0 && (
                  <div>
                    <p className="text-sm font-medium text-gray-700 mb-2">{importPreview.length} valid row(s) ready to import</p>
                    <div className="overflow-x-auto border rounded-lg max-h-40 overflow-y-auto">
                      <table className="w-full text-sm">
                        <thead className="bg-gray-50 sticky top-0">
                          <tr className="border-b">
                            <th className="text-left p-2 font-semibold text-gray-600">Name</th>
                            <th className="text-left p-2 font-semibold text-gray-600">Email</th>
                            <th className="text-left p-2 font-semibold text-gray-600">Subjects</th>
                          </tr>
                        </thead>
                        <tbody>
                          {importPreview.map((r, i) => (
                            <tr key={i} className="border-b last:border-0">
                              <td className="p-2">{r.full_name}</td>
                              <td className="p-2 text-xs">{r.email}</td>
                              <td className="p-2 text-xs">{(r.subjects || []).join(', ')}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

                <div className="flex gap-3 pt-2">
                  <button onClick={() => { setStaffMode(''); setImportFile(null); setImportErrors([]); setImportPreview([]); }}
                    className="btn-secondary gap-1"><ChevronLeft className="h-4 w-4" /> Back</button>
                  {importPreview.length > 0 && (
                    <button onClick={handleConfirmImport} disabled={importing}
                      className="btn-primary flex-1 gap-2">
                      {importing ? 'Importing…' : <><Upload className="h-4 w-4" /> Import {importPreview.length} Teacher(s)</>}
                    </button>
                  )}
                </div>
              </div>
            )}

            {/* Credentials Display */}
            {showCredentials && (
              <div className="mt-6 border border-emerald-200 rounded-xl overflow-hidden">
                <div className="bg-emerald-50 p-4 border-b border-emerald-200">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="font-semibold text-emerald-800 flex items-center gap-2">
                        <Check className="h-5 w-5" /> {credentials.length} Account(s) Created
                      </h3>
                      <p className="text-xs text-emerald-600 mt-0.5">
                        These are one-time credentials. Teachers must change password on first login.
                      </p>
                    </div>
                    <button onClick={() => setShowCredentials(false)} className="text-emerald-400 hover:text-emerald-600"><X className="h-5 w-5" /></button>
                  </div>
                </div>
                <div className="overflow-x-auto max-h-72 overflow-y-auto">
                  <table className="w-full text-sm">
                    <thead className="bg-gray-50 sticky top-0">
                      <tr className="border-b">
                        <th className="text-left p-2.5 font-semibold text-gray-600">Employee #</th>
                        <th className="text-left p-2.5 font-semibold text-gray-600">Name</th>
                        <th className="text-left p-2.5 font-semibold text-gray-600">Username</th>
                        <th className="text-left p-2.5 font-semibold text-gray-600">Temp Password</th>
                        <th className="text-left p-2.5 font-semibold text-gray-600">Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {credentials.map(t => (
                        <tr key={t.id} className="border-b last:border-0 hover:bg-gray-50">
                          <td className="p-2.5 font-mono text-xs">{t.employee_number}</td>
                          <td className="p-2.5">{t.full_name}</td>
                          <td className="p-2.5 font-mono text-xs">{t.email}</td>
                          <td className="p-2.5">
                            <code className="bg-amber-50 px-2 py-0.5 rounded font-mono text-xs tracking-wider text-amber-800">
                              {t.temp_password}
                            </code>
                          </td>
                          <td className="p-2.5">
                            <span className="rounded-full bg-amber-100 text-amber-700 px-2 py-0.5 text-xs font-medium">Pending</span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div className="bg-gray-50 p-3 flex gap-2 border-t">
                  <button onClick={handlePrintCredentials} className="btn-secondary text-xs gap-1.5">
                    <Printer className="h-3.5 w-3.5" /> Print
                  </button>
                  <button onClick={() => {
                    const csv = [['Employee #','Name','Username','Temp Password','Status'],
                      ...credentials.map(t => [t.employee_number, t.full_name, t.email, t.temp_password, 'Pending']),
                    ].map(r => r.map(c => `"${c}"`).join(',')).join('\n');
                    const blob = new Blob([csv], { type: 'text/csv' });
                    const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = 'staff_credentials.csv'; a.click();
                  }} className="btn-secondary text-xs gap-1.5">
                    <Download className="h-3.5 w-3.5" /> CSV
                  </button>
                </div>
              </div>
            )}

            {/* Finish or Next */}
            {isComplete && (
              <button onClick={handleFinish} className="btn-primary w-full mt-4 gap-2">
                <Check className="h-4 w-4" /> Complete Setup
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
