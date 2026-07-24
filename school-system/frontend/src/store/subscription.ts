import { create } from 'zustand';
import api from '@/services/api';

interface SubscriptionState {
  status: 'active' | 'trial' | 'read_only' | 'expired' | 'past_due' | 'pending_verification' | null;
  isReadOnly: boolean;
  message: string | null;
  daysLeft: number | null;
  loading: boolean;

  fetchStatus: () => Promise<void>;
  setBlocked: (message: string) => void;
}

export const useSubscriptionStore = create<SubscriptionState>((set) => ({
  status: null,
  isReadOnly: false,
  message: null,
  daysLeft: null,
  loading: false,

  fetchStatus: async () => {
    set({ loading: true });
    try {
      // Platform admins don't have schools/subscriptions
      const userRaw = localStorage.getItem('user');
      if (userRaw) {
        const user = JSON.parse(userRaw);
        if (user.role === 'platform_admin') {
          set({ status: 'active', isReadOnly: false, loading: false });
          return;
        }
      }

      const { data } = await api.get('/billing/subscription/trial-status');
      set({
        status: data.status,
        isReadOnly: !!data.is_read_only,
        message: data.message,
        daysLeft: data.days_left,
        loading: false,
      });
    } catch (err) {
      console.error('Failed to fetch trial status', err);
      set({ loading: false });
    }
  },

  setBlocked: (message: string) => {
    set({
      status: 'read_only',
      isReadOnly: true,
      message,
    });
  },
}));
