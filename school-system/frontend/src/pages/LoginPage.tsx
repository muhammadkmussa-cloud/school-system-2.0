import { useState } from 'react';
import { useNavigate, Navigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import toast from 'react-hot-toast';
import { useAuthStore } from '@/store/auth';
import api from '@/services/api';
import { LogIn, Eye, EyeOff, School, User, Lock } from 'lucide-react';

interface LoginForm {
  username: string;
  password: string;
}

export default function LoginPage() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const user = useAuthStore((s) => s.user);
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [showPw, setShowPw] = useState(false);
  const { register, handleSubmit, formState: { errors } } = useForm<LoginForm>();

  // If already authenticated, redirect to first-login if needed, else home
  if (isAuthenticated && user) {
    if (user.must_change_password) return <Navigate to="/first-login" replace />;
    return <Navigate to="/" replace />;
  }

  const onSubmit = async (data: LoginForm) => {
    setLoading(true);
    try {
      const res = await api.post('/auth/login', {
        username: data.username,
        password: data.password,
      });
      const { access_token, refresh_token, user } = res.data;
      useAuthStore.getState().login(access_token, refresh_token, user);
      toast.success(`Welcome back, ${user.full_name}!`);

      if (user.must_change_password) {
        navigate('/first-login');
      } else {
        navigate('/');
      }
    } catch (err: any) {
      const msg = err.response?.data?.detail || 'Login failed';
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-brand-50 to-blue-100 px-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-brand-600 text-white text-xl font-bold shadow-lg">
            EF
          </div>
          <h1 className="text-2xl font-bold text-gray-900">School Management System</h1>
          <p className="mt-2 text-sm text-gray-500">
            Teacher-Centred School Management
          </p>
        </div>

        <div className="card">
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
            <div>
              <label htmlFor="username" className="label">
                Username or Email
              </label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                <input
                  id="username"
                  type="text"
                  className="input-field pl-10"
                  placeholder="e.g. admin@example.com"
                  {...register('username', { required: 'Username or Email is required' })}
                />
              </div>
              {errors.username && (
                <p className="mt-1 text-xs text-red-600">{errors.username.message}</p>
              )}
            </div>

            <div>
              <label htmlFor="password" className="label">
                Password
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                <input
                  id="password"
                  type={showPw ? 'text' : 'password'}
                  className="input-field pl-10 pr-10"
                  placeholder="••••••••"
                  {...register('password', { required: 'Password is required' })}
                />
                <button
                  type="button"
                  onClick={() => setShowPw(!showPw)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                >
                  {showPw ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
              {errors.password && (
                <p className="mt-1 text-xs text-red-600">
                  {errors.password.message}
                </p>
              )}
            </div>

            <button
              type="submit"
              disabled={loading}
              className="btn-primary w-full gap-2 py-2.5"
            >
              {loading ? (
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
              ) : (
                <LogIn className="h-4 w-4" />
              )}
              {loading ? 'Signing in…' : 'Sign in'}
            </button>
          </form>
        </div>

        <p className="mt-6 text-center text-xs text-gray-400">
          School Management System v1.0 — Secure, offline-capable school management
        </p>
      </div>
    </div>
  );
}
