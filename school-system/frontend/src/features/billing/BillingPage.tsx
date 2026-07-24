import { useEffect, useState } from 'react';
import api from '@/services/api';
import toast from 'react-hot-toast';
import {
  CreditCard, Smartphone, Check, Zap, Shield, Building2,
  ArrowRight, Receipt, History, AlertCircle, RefreshCw,
} from 'lucide-react';
import { useAuthStore } from '@/store/auth';

interface TierInfo {
  name: string; display: string;
  price_monthly_kes: number; price_yearly_kes: number;
  max_students: number; max_teachers: number; max_campuses: number;
  highlights: string[]; features: string[];
  api_access: boolean; priority_support: boolean;
  custom_branding: boolean; dedicated_onboarding: boolean;
  color: string;
}

interface Subscription {
  id: string; tier: string; tier_display: string;
  status: string; billing_cycle: string;
  current_period_end: string | null;
  payment_method: string | null; auto_renew: boolean;
  trial_ends_at: string | null;
  limits: { max_students: number; max_teachers: number; api_access: boolean; priority_support: boolean };
}

export default function BillingPage() {
  const user = useAuthStore(s => s.user);
  const [tiers, setTiers] = useState<TierInfo[]>([]);
  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const [invoices, setInvoices] = useState<any[]>([]);
  const [payments, setPayments] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<'plans' | 'billing' | 'history'>('plans');
  const [selectedTier, setSelectedTier] = useState('');
  const [billingCycle, setBillingCycle] = useState<'monthly' | 'yearly'>('monthly');
  const [paymentMethod, setPaymentMethod] = useState<'mpesa' | 'paystack'>('mpesa');
  const [mpesaPhone, setMpesaPhone] = useState('');
  const [pendingPayment, setPendingPayment] = useState<any>(null);
  const [upgrading, setUpgrading] = useState(false);

  useEffect(() => {
    const load = async () => {
      try {
        const [tiersRes, subRes] = await Promise.all([
          api.get('/billing/tiers'),
          api.get('/billing/subscription').catch(() => ({ data: null })),
        ]);
        setTiers(tiersRes.data.tiers);
        if (subRes.data?.subscription) {
          setSubscription(subRes.data.subscription);
          setInvoices(subRes.data.invoices || []);
          setPayments(subRes.data.payments || []);
        }
      } catch { toast.error('Failed to load billing data'); }
      finally { setLoading(false); }
    };
    load();
  }, []);

  const handleUpgrade = async () => {
    if (!selectedTier) { toast.error('Select a plan'); return; }
    if (paymentMethod === 'mpesa' && !mpesaPhone) {
      toast.error('Enter M-Pesa phone number (2547XXXXXXXX)');
      return;
    }

    setUpgrading(true);
    try {
      const payload: any = {
        tier: selectedTier,
        billing_cycle: billingCycle,
        payment_method: paymentMethod,
      };
      if (paymentMethod === 'mpesa') payload.mpesa_phone = mpesaPhone;
      if (paymentMethod === 'paystack') payload.paystack_email = user?.email;

      const { data } = await api.post('/billing/subscription/change', payload);

      if (data.requires_payment) {
        // Initiate payment
        if (paymentMethod === 'mpesa') {
          const payRes = await api.post('/billing/mpesa/pay', {
            invoice_id: data.invoice_id,
            phone_number: mpesaPhone,
          });
          setPendingPayment({ ...payRes.data, method: 'mpesa' });
          toast.success('M-Pesa push sent! Check your phone.');
        } else {
          const payRes = await api.post('/billing/paystack/pay', {
            invoice_id: data.invoice_id,
            email: user?.email,
          });
          setPendingPayment({ ...payRes.data, method: 'paystack' });
          if (payRes.data.authorization_url) {
            window.open(payRes.data.authorization_url, '_blank');
          }
          toast.success('Paystack checkout opened in new tab.');
        }
      } else {
        toast.success(`Switched to ${data.tier} plan!`);
        const { data: subData } = await api.get('/billing/subscription');
        setSubscription(subData.subscription);
      }
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Upgrade failed');
    } finally {
      setUpgrading(false);
    }
  };

  const verifyPayment = async () => {
    if (!pendingPayment) return;
    try {
      if (pendingPayment.method === 'mpesa') {
        const { data } = await api.post('/billing/mpesa/query', null, {
          params: { checkout_request_id: pendingPayment.checkout_request_id },
        });
        toast.success('Payment status checked. Refresh billing page.');
      }
      setPendingPayment(null);
      const { data } = await api.get('/billing/subscription');
      setSubscription(data.subscription);
      setInvoices(data.invoices || []);
      setPayments(data.payments || []);
    } catch { toast.error('Verification failed'); }
  };

  if (loading) return <div className="flex justify-center py-12"><div className="h-8 w-8 animate-spin rounded-full border-2 border-brand-600 border-t-transparent" /></div>;

  const isAdmin = user?.role === 'school_admin' || user?.role === 'platform_admin';

  return (
    <div>
      <div className="page-header">
        <h2 className="text-2xl font-bold text-gray-900">Billing & Plans</h2>
        {subscription && (
          <span className="text-sm px-3 py-1 rounded-full font-medium"
            style={{ backgroundColor: tiers.find(t => t.name === subscription.tier)?.color + '20' || '#e5e7eb',
                     color: tiers.find(t => t.name === subscription.tier)?.color || '#6b7280' }}>
            {subscription.tier_display} · {subscription.status}
          </span>
        )}
      </div>

      {/* Tabs */}
      <div className="mb-6 flex gap-1 rounded-lg bg-gray-100 p-1 w-fit">
        {[
          { key: 'plans' as const, label: 'Plans', icon: Zap },
          { key: 'billing' as const, label: 'Payment', icon: CreditCard },
          { key: 'history' as const, label: 'History', icon: Receipt },
        ].map(t => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className={`flex items-center gap-1.5 px-4 py-2 text-sm font-medium rounded-md transition-colors ${
              tab === t.key ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'
            }`}>
            <t.icon className="h-4 w-4" /> {t.label}
          </button>
        ))}
      </div>

      {/* Plans Tab */}
      {tab === 'plans' && (
        <>
          {/* Billing toggle */}
          <div className="flex justify-center mb-8">
            <div className="flex items-center gap-2 rounded-lg bg-gray-100 p-1">
              <button onClick={() => setBillingCycle('monthly')}
                className={`px-4 py-1.5 text-sm rounded-md ${billingCycle === 'monthly' ? 'bg-white shadow-sm font-medium' : 'text-gray-500'}`}>
                Monthly
              </button>
              <button onClick={() => setBillingCycle('yearly')}
                className={`px-4 py-1.5 text-sm rounded-md flex items-center gap-1 ${billingCycle === 'yearly' ? 'bg-white shadow-sm font-medium' : 'text-gray-500'}`}>
                Yearly
                <span className="text-xs text-green-600 font-bold">-17%</span>
              </button>
            </div>
          </div>

          {/* Tier cards */}
          <div className="grid gap-6 lg:grid-cols-4">
            {tiers.map(tier => {
              const isCurrent = subscription?.tier === tier.name;
              const price = billingCycle === 'monthly' ? tier.price_monthly_kes : tier.price_yearly_kes;
              const priceDisplay = price === 0 ? 'Free' : `KES ${price.toLocaleString()}`;
              const period = price === 0 ? '' : `/${billingCycle === 'monthly' ? 'mo' : 'yr'}`;

              return (
                <div key={tier.name}
                  className={`card relative flex flex-col border-2 transition-all ${
                    isCurrent ? 'border-brand-500 ring-1 ring-brand-500' :
                    selectedTier === tier.name ? 'border-brand-400' : 'border-gray-200 hover:border-gray-300'
                  }`}
                  onClick={() => isAdmin && tier.name !== 'free' && setSelectedTier(tier.name)}
                  style={{ cursor: isAdmin && tier.name !== 'free' ? 'pointer' : 'default' }}>
                  {isCurrent && (
                    <span className="absolute -top-3 left-1/2 -translate-x-1/2 bg-brand-600 text-white text-xs px-3 py-0.5 rounded-full font-medium">
                      Current Plan
                    </span>
                  )}

                  <div className="text-center mb-4">
                    <h3 className="text-lg font-bold" style={{ color: tier.color }}>{tier.display}</h3>
                    <div className="mt-2">
                      <span className="text-3xl font-extrabold">{priceDisplay}</span>
                      <span className="text-sm text-gray-400">{period}</span>
                    </div>
                    <p className="text-xs text-gray-400 mt-1">
                      {tier.max_students === 0 ? 'No student DB' :
                       tier.max_students >= 10000 ? 'Unlimited students' :
                       `Up to ${tier.max_students.toLocaleString()} students`}
                    </p>
                  </div>

                  <ul className="space-y-2 mb-6 flex-1">
                    {tier.highlights.map(h => (
                      <li key={h} className="flex items-start gap-2 text-sm text-gray-600">
                        <Check className="h-4 w-4 text-green-500 mt-0.5 flex-shrink-0" />
                        {h}
                      </li>
                    ))}
                    {tier.api_access && (
                      <li className="flex items-start gap-2 text-sm text-gray-600">
                        <Shield className="h-4 w-4 text-purple-500 mt-0.5 flex-shrink-0" /> API Access
                      </li>
                    )}
                    {tier.custom_branding && (
                      <li className="flex items-start gap-2 text-sm text-gray-600">
                        <Building2 className="h-4 w-4 text-blue-500 mt-0.5 flex-shrink-0" /> Custom Branding
                      </li>
                    )}
                  </ul>

                  {isAdmin && tier.name !== 'free' && !isCurrent && (
                    <button
                      onClick={(e) => { e.stopPropagation(); setSelectedTier(tier.name); }}
                      className={`w-full py-2 rounded-lg text-sm font-medium transition-colors ${
                        selectedTier === tier.name
                          ? 'bg-brand-600 text-white'
                          : 'border border-gray-300 text-gray-700 hover:bg-gray-50'
                      }`}>
                      {selectedTier === tier.name ? 'Selected ✓' : 'Choose ' + tier.display}
                    </button>
                  )}
                  {isCurrent && tier.name !== 'free' && (
                    <div className="w-full py-2 rounded-lg text-sm font-medium text-center bg-gray-100 text-gray-500">
                      Current Plan
                    </div>
                  )}
                  {tier.name === 'free' && (
                    <div className="w-full py-2 rounded-lg text-sm font-medium text-center bg-gray-50 text-gray-400">
                      {isCurrent ? 'Active' : 'Default'}
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Payment method selection */}
          {selectedTier && isAdmin && (
            <div className="card mt-6">
              <h3 className="text-lg font-semibold mb-4">Payment Method</h3>
              <div className="grid gap-4 sm:grid-cols-2 mb-4">
                <button onClick={() => setPaymentMethod('mpesa')}
                  className={`flex items-center gap-3 p-4 rounded-lg border-2 transition-colors ${
                    paymentMethod === 'mpesa' ? 'border-green-500 bg-green-50' : 'border-gray-200 hover:border-gray-300'
                  }`}>
                  <Smartphone className="h-8 w-8 text-green-600" />
                  <div className="text-left">
                    <p className="font-semibold">M-Pesa</p>
                    <p className="text-xs text-gray-500">Pay via STK Push (Kenya)</p>
                  </div>
                </button>
                <button onClick={() => setPaymentMethod('paystack')}
                  className={`flex items-center gap-3 p-4 rounded-lg border-2 transition-colors ${
                    paymentMethod === 'paystack' ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:border-gray-300'
                  }`}>
                  <CreditCard className="h-8 w-8 text-blue-600" />
                  <div className="text-left">
                    <p className="font-semibold">Paystack</p>
                    <p className="text-xs text-gray-500">Card / Bank / Mobile Money</p>
                  </div>
                </button>
              </div>

              {paymentMethod === 'mpesa' && (
                <div className="mb-4">
                  <label className="label">M-Pesa Phone Number</label>
                  <input className="input-field" placeholder="254712345678"
                    value={mpesaPhone} onChange={e => setMpesaPhone(e.target.value)} />
                  <p className="text-xs text-gray-400 mt-1">Safaricom number in 2547XXXXXXXX format</p>
                </div>
              )}

              <button onClick={handleUpgrade} disabled={upgrading}
                className="btn-primary w-full gap-2 py-3">
                {upgrading ? (
                  <RefreshCw className="h-4 w-4 animate-spin" />
                ) : (
                  <ArrowRight className="h-4 w-4" />
                )}
                {upgrading ? 'Processing…' : `Upgrade to ${tiers.find(t => t.name === selectedTier)?.display} · KES ${billingCycle === 'monthly' ? tiers.find(t => t.name === selectedTier)?.price_monthly_kes?.toLocaleString() : tiers.find(t => t.name === selectedTier)?.price_yearly_kes?.toLocaleString()}/${billingCycle === 'monthly' ? 'mo' : 'yr'}`}
              </button>
            </div>
          )}

          {/* Pending payment */}
          {pendingPayment && (
            <div className="card mt-4 border-amber-300 bg-amber-50">
              <div className="flex items-center gap-3">
                <AlertCircle className="h-5 w-5 text-amber-600" />
                <div>
                  <p className="font-medium text-amber-800">Payment in progress</p>
                  <p className="text-sm text-amber-600">
                    {pendingPayment.method === 'mpesa'
                      ? 'Check your phone for the M-Pesa prompt and enter your PIN.'
                      : 'Complete payment in the Paystack checkout tab.'}
                  </p>
                </div>
                <button onClick={verifyPayment} className="btn-secondary text-xs ml-auto gap-1">
                  <RefreshCw className="h-3 w-3" /> Check Status
                </button>
              </div>
            </div>
          )}
        </>
      )}

      {/* Billing Tab */}
      {tab === 'billing' && (
        <div className="card max-w-lg mx-auto">
          <h3 className="text-lg font-semibold mb-4">Current Subscription</h3>
          {subscription ? (
            <div className="space-y-4">
              <div className="flex justify-between py-2 border-b">
                <span className="text-gray-500">Plan</span>
                <span className="font-semibold">{subscription.tier_display}</span>
              </div>
              <div className="flex justify-between py-2 border-b">
                <span className="text-gray-500">Status</span>
                <span className={`font-medium capitalize ${
                  subscription.status === 'active' ? 'text-green-600' :
                  subscription.status === 'past_due' ? 'text-red-600' :
                  'text-yellow-600'
                }`}>{subscription.status}</span>
              </div>
              <div className="flex justify-between py-2 border-b">
                <span className="text-gray-500">Billing Cycle</span>
                <span className="capitalize">{subscription.billing_cycle}</span>
              </div>
              <div className="flex justify-between py-2 border-b">
                <span className="text-gray-500">Students</span>
                <span>Up to {subscription.limits.max_students === 0 ? 'N/A (Free)' : subscription.limits.max_students.toLocaleString()}</span>
              </div>
              <div className="flex justify-between py-2 border-b">
                <span className="text-gray-500">Teachers</span>
                <span>Up to {subscription.limits.max_teachers.toLocaleString()}</span>
              </div>
              {subscription.current_period_end && (
                <div className="flex justify-between py-2 border-b">
                  <span className="text-gray-500">Renews</span>
                  <span>{new Date(subscription.current_period_end).toLocaleDateString()}</span>
                </div>
              )}
              {subscription.trial_ends_at && (
                <div className="flex justify-between py-2 border-b">
                  <span className="text-gray-500">Trial Ends</span>
                  <span className="text-amber-600 font-medium">
                    {new Date(subscription.trial_ends_at).toLocaleDateString()}
                  </span>
                </div>
              )}
            </div>
          ) : (
            <p className="text-gray-400 py-8 text-center">No active subscription. Select a plan.</p>
          )}
        </div>
      )}

      {/* History Tab */}
      {tab === 'history' && (
        <div className="space-y-6">
          <div className="card">
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Receipt className="h-5 w-5" /> Invoices
            </h3>
            {invoices.length === 0 ? (
              <p className="text-gray-400 py-4 text-center text-sm">No invoices yet.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead><tr className="border-b">
                    <th className="table-header">Invoice</th><th className="table-header">Amount</th>
                    <th className="table-header">Status</th><th className="table-header">Date</th>
                  </tr></thead>
                  <tbody>
                    {invoices.map(inv => (
                      <tr key={inv.id} className="border-b border-gray-50">
                        <td className="table-cell font-mono text-xs">{inv.number}</td>
                        <td className="table-cell font-medium">KES {inv.amount_kes?.toLocaleString()}</td>
                        <td className="table-cell">
                          <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                            inv.status === 'paid' ? 'bg-green-100 text-green-700' :
                            inv.status === 'overdue' ? 'bg-red-100 text-red-700' :
                            'bg-yellow-100 text-yellow-700'
                          }`}>{inv.status}</span>
                        </td>
                        <td className="table-cell text-xs text-gray-500">
                          {inv.due_date ? new Date(inv.due_date).toLocaleDateString() : '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          <div className="card">
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <History className="h-5 w-5" /> Payment History
            </h3>
            {payments.length === 0 ? (
              <p className="text-gray-400 py-4 text-center text-sm">No payments yet.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead><tr className="border-b">
                    <th className="table-header">Gateway</th><th className="table-header">Amount</th>
                    <th className="table-header">Status</th><th className="table-header">Reference</th>
                    <th className="table-header">Date</th>
                  </tr></thead>
                  <tbody>
                    {payments.map(p => (
                      <tr key={p.id} className="border-b border-gray-50">
                        <td className="table-cell">
                          {p.gateway === 'mpesa' ? (
                            <span className="flex items-center gap-1"><Smartphone className="h-3 w-3 text-green-600" /> M-Pesa</span>
                          ) : p.gateway === 'paystack' ? (
                            <span className="flex items-center gap-1"><CreditCard className="h-3 w-3 text-blue-600" /> Paystack</span>
                          ) : (
                            p.gateway
                          )}
                        </td>
                        <td className="table-cell font-medium">KES {p.amount_kes?.toLocaleString()}</td>
                        <td className="table-cell">
                          <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                            p.status === 'completed' ? 'bg-green-100 text-green-700' :
                            p.status === 'failed' ? 'bg-red-100 text-red-700' :
                            'bg-gray-100 text-gray-600'
                          }`}>{p.status}</span>
                        </td>
                        <td className="table-cell font-mono text-xs">
                          {p.mpesa_receipt || p.gateway_reference?.slice(0, 16) || '—'}
                        </td>
                        <td className="table-cell text-xs text-gray-500">
                          {p.created_at ? new Date(p.created_at).toLocaleDateString() : '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
