import { useState, useRef } from 'react';
import api from '@/services/api';
import toast from 'react-hot-toast';
import { Upload, FileSpreadsheet, Download, CheckCircle, XCircle, AlertTriangle } from 'lucide-react';

type ImportType = 'students' | 'teachers' | 'marks';

export default function ImportManager() {
  const [importType, setImportType] = useState<ImportType>('students');
  const [file, setFile] = useState<File | null>(null);
  const [assessmentId, setAssessmentId] = useState('');
  const [loading, setLoading] = useState(false);
  const [report, setReport] = useState<any>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const handleImport = async () => {
    if (!file) { toast.error('Please select a file'); return; }
    setLoading(true);

    const formData = new FormData();
    formData.append('file', file);

    try {
      let url = `/imports/${importType}/csv`;
      if (importType === 'marks') {
        url += `?assessment_id=${assessmentId}`;
      }

      const { data } = await api.post(url, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setReport(data);

      if (data.success > 0) toast.success(`${data.success} records imported!`);
      if (data.errors?.length > 0) toast.error(`${data.errors.length} errors found`);
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Import failed');
    } finally {
      setLoading(false);
    }
  };

  const downloadTemplate = async () => {
    window.open(`/api/v1/imports/templates/${importType}`, '_blank');
  };

  const importTypes: { key: ImportType; label: string; description: string }[] = [
    { key: 'students', label: 'Students', description: 'admission_number, full_name, gender, date_of_birth, class_name, stream_name, parent_*' },
    { key: 'teachers', label: 'Teachers', description: 'employee_number, full_name, email, phone' },
    { key: 'marks', label: 'Marks', description: 'admission_number, score, remarks (requires assessment ID)' },
  ];

  return (
    <div>
      <div className="page-header">
        <h2 className="text-2xl font-bold text-gray-900">Bulk Import</h2>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Import form */}
        <div className="card">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Upload className="h-5 w-5 text-brand-600" /> Import Data
          </h3>

          {/* Type selector */}
          <div className="mb-4 flex gap-1 rounded-lg bg-gray-100 p-1 w-fit">
            {importTypes.map(t => (
              <button key={t.key} onClick={() => { setImportType(t.key); setReport(null); setFile(null); if (fileRef.current) fileRef.current.value = ''; }}
                className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${importType === t.key ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'}`}>
                {t.label}
              </button>
            ))}
          </div>

          <p className="text-sm text-gray-500 mb-4">{importTypes.find(t => t.key === importType)?.description}</p>

          {importType === 'marks' && (
            <div className="mb-4">
              <label className="label">Assessment ID</label>
              <input className="input-field" placeholder="Paste assessment UUID" value={assessmentId}
                onChange={e => setAssessmentId(e.target.value)} />
            </div>
          )}

          {/* File upload area */}
          <div
            className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center hover:border-brand-400 transition-colors cursor-pointer mb-4"
            onClick={() => fileRef.current?.click()}
          >
            <FileSpreadsheet className="mx-auto h-10 w-10 text-gray-400 mb-2" />
            <p className="text-sm text-gray-600">
              {file ? file.name : 'Click to select a CSV file'}
            </p>
            <p className="text-xs text-gray-400 mt-1">Max 10 MB</p>
            <input ref={fileRef} type="file" accept=".csv" className="hidden"
              onChange={e => setFile(e.target.files?.[0] || null)} />
          </div>

          <div className="flex gap-3">
            <button onClick={downloadTemplate} className="btn-secondary gap-1 text-xs">
              <Download className="h-3 w-3" /> Template
            </button>
            <button onClick={handleImport} disabled={loading || !file} className="btn-primary flex-1 gap-2">
              <Upload className="h-4 w-4" /> {loading ? 'Importing…' : 'Import CSV'}
            </button>
          </div>
        </div>

        {/* Report */}
        {report && (
          <div className="card">
            <h3 className="text-lg font-semibold mb-4">Import Report</h3>

            <div className="grid grid-cols-3 gap-3 mb-4">
              <div className="text-center p-3 bg-gray-50 rounded-lg">
                <p className="text-2xl font-bold">{report.total_rows}</p>
                <p className="text-xs text-gray-500">Total Rows</p>
              </div>
              <div className="text-center p-3 bg-green-50 rounded-lg">
                <p className="text-2xl font-bold text-green-700">{report.success}</p>
                <p className="text-xs text-green-600">Imported</p>
              </div>
              <div className="text-center p-3 bg-yellow-50 rounded-lg">
                <p className="text-2xl font-bold text-yellow-700">{report.skipped || 0}</p>
                <p className="text-xs text-yellow-600">Skipped</p>
              </div>
            </div>

            {report.errors?.length > 0 && (
              <div>
                <h4 className="text-sm font-medium text-red-700 mb-2 flex items-center gap-1">
                  <AlertTriangle className="h-4 w-4" /> Errors ({report.errors.length})
                </h4>
                <div className="max-h-48 overflow-y-auto space-y-1">
                  {report.errors.slice(0, 20).map((e: any, i: number) => (
                    <div key={i} className="text-xs text-red-600 bg-red-50 rounded px-2 py-1 flex items-center gap-1">
                      <XCircle className="h-3 w-3 flex-shrink-0" />
                      Row {e.row}: {e.error}
                    </div>
                  ))}
                  {report.errors.length > 20 && (
                    <p className="text-xs text-gray-400">…and {report.errors.length - 20} more errors</p>
                  )}
                </div>
              </div>
            )}

            {report.success > 0 && report.errors?.length === 0 && (
              <div className="text-center py-4">
                <CheckCircle className="mx-auto h-8 w-8 text-green-500 mb-2" />
                <p className="text-green-700 font-medium">All records imported successfully!</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
