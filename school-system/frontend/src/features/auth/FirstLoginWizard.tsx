import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import toast from 'react-hot-toast';
import { useAuthStore } from '@/store/auth';
import api from '@/services/api';
import { Eye, EyeOff, Check, Key, Mail, Phone, FileText } from 'lucide-react';
import clsx from 'clsx';

type StepId = 'password' | 'contact' | 'terms';

export default function FirstLoginWizard() {
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);

  const [step, setStep] = useState<StepId>('password');
  const [loading, setLoading] = useState(false);
  const [showPw, setShowPw] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [acceptTerms, setAcceptTerms] = useState(false);
  const [email, setEmail] = useState(user?.email || '');
  const [phone, setPhone] = useState(user?.phone || '');

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<{ new_password: string; confirm_password: string }>({
    defaultValues: { new_password: '', confirm_password: '' },
  });

  const newPassword = watch('new_password');

  // Redirect if already completed
  if (!user || !user.must_change_password) {
    navigate('/', { replace: true });
    return null;
  }

  const handlePasswordSubmit = async () => {
    setLoading(true);
    try {
      // Save password, email, phone, terms in sequence
      // The API validates all fields in one call
      const payload: any = {
        new_password: newPassword,
        accept_terms: acceptTerms,
      };
      if (email) payload.email = email;
      if (phone) payload.phone = phone;

      await api.post('/auth/first-login', payload);
      // Update store
      const updated = { ...user, must_change_password: false, terms_accepted: acceptTerms, profile_completed: true };
      useAuthStore.getState().setUser(updated);
      toast.success('Account setup complete!');
      navigate('/', { replace: true });
    } catch (err: any) {
      const msg = err.response?.data?.detail || 'Failed to complete setup';
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  const steps: { id: StepId; label: string; icon: React.ReactNode }[] = [
    { id: 'password', label: 'Set Password', icon: <Key className="h-4 w-4" /> },
    { id: 'contact', label: 'Contact Info', icon: <Mail className="h-4 w-4" /> },
    { id: 'terms', label: 'Terms of Service', icon: <FileText className="h-4 w-4" /> },
  ];

  const currentIdx = steps.findIndex((s) => s.id === step);

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-brand-50 to-blue-100 px-4">
      <div className="w-full max-w-lg">
        <div className="text-center mb-6">
          <h1 className="text-xl font-bold text-gray-900">Complete Your Account Setup</h1>
          <p className="mt-1 text-sm text-gray-500">
            Welcome, {user.full_name}! Please complete the following steps.
          </p>
        </div>

        {/* Step indicator */}
        <div className="flex items-center justify-center gap-2 mb-6">
          {steps.map((s, idx) => (
            <div key={s.id} className="flex items-center gap-2">
              <div
                className={clsx(
                  'flex h-8 w-8 items-center justify-center rounded-full text-xs font-semibold',
                  idx < currentIdx
                    ? 'bg-brand-600 text-white'
                    : idx === currentIdx
                    ? 'bg-brand-100 text-brand-700 ring-2 ring-brand-500'
                    : 'bg-gray-100 text-gray-400'
                )}
              >
                {idx < currentIdx ? <Check className="h-4 w-4" /> : idx + 1}
              </div>
              <span
                className={clsx(
                  'text-xs hidden sm:inline',
                  idx === currentIdx ? 'font-medium text-brand-700' : 'text-gray-400'
                )}
              >
                {s.label}
              </span>
              {idx < steps.length - 1 && <div className="h-px w-6 bg-gray-200" />}
            </div>
          ))}
        </div>

        <div className="card">
          {/* Step 1: Set new password */}
          {step === 'password' && (
            <div>
              <h2 className="text-lg font-semibold mb-4">Set Your Password</h2>
              <p className="text-sm text-gray-500 mb-4">
                You must change your temporary password to continue.
              </p>

              <div className="space-y-4">
                <div>
                  <label htmlFor="new_password" className="label">New Password</label>
                  <div className="relative">
                    <Key className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                    <input
                      id="new_password"
                      type={showPw ? 'text' : 'password'}
                      className="input-field pl-10 pr-10"
                      placeholder="At least 8 characters"
                      {...register('new_password', {
                        required: 'Password is required',
                        minLength: { value: 8, message: 'At least 8 characters' },
                      })}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPw(!showPw)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                    >
                      {showPw ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  </div>
                  {errors.new_password && (
                    <p className="mt-1 text-xs text-red-600">{errors.new_password.message}</p>
                  )}
                </div>

                <div>
                  <label htmlFor="confirm_password" className="label">Confirm Password</label>
                  <div className="relative">
                    <Key className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                    <input
                      id="confirm_password"
                      type={showConfirm ? 'text' : 'password'}
                      className="input-field pl-10 pr-10"
                      placeholder="Repeat your password"
                      {...register('confirm_password', {
                        required: 'Please confirm your password',
                        validate: (v) => v === newPassword || 'Passwords do not match',
                      })}
                    />
                    <button
                      type="button"
                      onClick={() => setShowConfirm(!showConfirm)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                    >
                      {showConfirm ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  </div>
                  {errors.confirm_password && (
                    <p className="mt-1 text-xs text-red-600">{errors.confirm_password.message}</p>
                  )}
                </div>
              </div>

              <div className="flex justify-end mt-6">
                <button
                  type="button"
                  onClick={handleSubmit(() => setStep('contact'))}
                  className="btn-primary gap-2"
                >
                  Continue <Mail className="h-4 w-4" />
                </button>
              </div>
            </div>
          )}

          {/* Step 2: Contact Info */}
          {step === 'contact' && (
            <div>
              <h2 className="text-lg font-semibold mb-4">Confirm Contact Information</h2>
              <p className="text-sm text-gray-500 mb-4">
                Verify your email and provide a phone number for account recovery.
              </p>

              <div className="space-y-4">
                <div>
                  <label htmlFor="email" className="label">Email Address</label>
                  <div className="relative">
                    <Mail className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                    <input
                      id="email"
                      type="email"
                      className="input-field pl-10"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="your@email.com"
                    />
                  </div>
                </div>

                <div>
                  <label htmlFor="phone" className="label">Phone Number</label>
                  <div className="relative">
                    <Phone className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                    <input
                      id="phone"
                      type="tel"
                      className="input-field pl-10"
                      value={phone}
                      onChange={(e) => setPhone(e.target.value)}
                      placeholder="+254 7XX XXX XXX"
                    />
                  </div>
                </div>
              </div>

              <div className="flex justify-between mt-6">
                <button
                  type="button"
                  onClick={() => setStep('password')}
                  className="btn-secondary gap-2"
                >
                  Back
                </button>
                <button
                  type="button"
                  onClick={() => setStep('terms')}
                  className="btn-primary gap-2"
                >
                  Continue <FileText className="h-4 w-4" />
                </button>
              </div>
            </div>
          )}

          {/* Step 3: Terms of Service */}
          {step === 'terms' && (
            <div>
              <h2 className="text-lg font-semibold mb-4">Terms of Service</h2>
              <p className="text-sm text-gray-500 mb-4">
                Please read and accept the terms of service to continue.
              </p>

              <div className="max-h-60 overflow-y-auto border rounded-lg p-4 bg-gray-50 text-sm text-gray-600 mb-4">
                <h3 className="font-semibold text-gray-800 mb-2">School Management System Terms of Service</h3>
                <p className="mb-2">
                  By using School Management System, you agree to the following terms and conditions:
                </p>
                <ul className="list-disc list-inside space-y-1">
                  <li>You are responsible for maintaining the confidentiality of your account credentials.</li>
                  <li>You agree not to share your login credentials with unauthorized personnel.</li>
                  <li>All student and staff data must be handled in accordance with applicable privacy laws.</li>
                  <li>The platform may be used solely for legitimate educational administration purposes.</li>
                  <li>You agree to report any security breaches or suspicious activity immediately.</li>
                  <li>School Management System reserves the right to suspend accounts that violate these terms.</li>
                </ul>
              </div>

              <label className="flex items-start gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={acceptTerms}
                  onChange={(e) => setAcceptTerms(e.target.checked)}
                  className="mt-1 h-4 w-4 rounded border-gray-300 text-brand-600 focus:ring-brand-500"
                />
                <span className="text-sm text-gray-600">
                  I have read and agree to the{' '}
                  <span className="text-brand-600 font-medium hover:underline cursor-pointer">
                    Terms of Service
                  </span>{' '}
                  and{' '}
                  <span className="text-brand-600 font-medium hover:underline cursor-pointer">
                    Privacy Policy
                  </span>
                </span>
              </label>

              <div className="flex justify-between mt-6">
                <button
                  type="button"
                  onClick={() => setStep('contact')}
                  className="btn-secondary gap-2"
                >
                  Back
                </button>
                <button
                  type="button"
                  onClick={handlePasswordSubmit}
                  disabled={loading || !acceptTerms}
                  className="btn-primary gap-2"
                >
                  {loading ? (
                    <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                  ) : (
                    <Check className="h-4 w-4" />
                  )}
                  {loading ? 'Saving…' : 'Complete Setup'}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
