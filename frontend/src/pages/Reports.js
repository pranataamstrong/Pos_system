import { useEffect, useState } from "react";
import api, { rupiah } from "@/lib/api";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import {
  ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid,
  BarChart, Bar, PieChart, Pie, Cell, Legend,
} from "recharts";
import { TrendingUp, Wallet, Receipt, Package, Loader2, AlertTriangle } from "lucide-react";

const CHART_COLORS = ["#4338CA", "#10B981", "#F59E0B", "#0EA5E9", "#EC4899", "#8B5CF6", "#EF4444", "#14B8A6"];

const todayStr = () => new Date().toISOString().slice(0, 10);
const daysAgo = (n) => new Date(Date.now() - n * 86400000).toISOString().slice(0, 10);

function StatCard({ icon: Icon, label, value, tint }) {
  return (
    <div className="rounded-lg border border-border bg-card p-5 transition-transform duration-200 hover:-translate-y-1">
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg" style={{ background: `${tint}1a`, color: tint }}>
          <Icon className="h-5 w-5" />
        </div>
        <span className="text-xs font-bold uppercase tracking-widest text-muted-foreground">{label}</span>
      </div>
      <p className="mt-4 font-display text-2xl font-semibold">{value}</p>
    </div>
  );
}

export default function Reports() {
  const [start, setStart] = useState(daysAgo(29));
  const [end, setEnd] = useState(todayStr());
  const [loading, setLoading] = useState(true);
  const [summary, setSummary] = useState(null);
  const [overTime, setOverTime] = useState([]);
  const [topProducts, setTopProducts] = useState([]);
  const [byCategory, setByCategory] = useState([]);
  const [payMethods, setPayMethods] = useState([]);
  const [lowStock, setLowStock] = useState([]);

  const load = async () => {
    setLoading(true);
    const q = { params: { start, end } };
    try {
      const [s, o, t, c, p, l] = await Promise.all([
        api.get("/reports/summary", q),
        api.get("/reports/sales-over-time", q),
        api.get("/reports/top-products", q),
        api.get("/reports/by-category", q),
        api.get("/reports/payment-methods", q),
        api.get("/reports/low-stock"),
      ]);
      setSummary(s.data);
      setOverTime(o.data.map((d) => ({ ...d, label: d.date.slice(5) })));
      setTopProducts(t.data);
      setByCategory(c.data);
      setPayMethods(p.data);
      setLowStock(l.data);
    } finally { setLoading(false); }
  };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, []);

  return (
    <div className="h-screen overflow-y-auto p-8">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl font-semibold">Laporan</h1>
          <p className="text-sm text-muted-foreground mt-1">Analisis penjualan bisnis Anda</p>
        </div>
        <div className="flex items-end gap-3">
          <div className="space-y-1.5">
            <Label className="text-xs">Dari</Label>
            <Input type="date" value={start} onChange={(e) => setStart(e.target.value)} className="w-40" data-testid="report-start-date" />
          </div>
          <div className="space-y-1.5">
            <Label className="text-xs">Sampai</Label>
            <Input type="date" value={end} onChange={(e) => setEnd(e.target.value)} className="w-40" data-testid="report-end-date" />
          </div>
          <Button onClick={load} data-testid="apply-filter-button">Terapkan</Button>
        </div>
      </div>

      {loading ? (
        <div className="flex h-64 items-center justify-center"><Loader2 className="h-6 w-6 animate-spin text-primary" /></div>
      ) : (
        <div className="space-y-6">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard icon={Wallet} label="Total Penjualan" value={rupiah(summary?.total_sales)} tint="#4338CA" />
            <StatCard icon={TrendingUp} label="Total Profit" value={rupiah(summary?.total_profit)} tint="#10B981" />
            <StatCard icon={Receipt} label="Transaksi" value={summary?.transactions || 0} tint="#F59E0B" />
            <StatCard icon={Package} label="Item Terjual" value={summary?.items_sold || 0} tint="#0EA5E9" />
          </div>

          <div className="rounded-lg border border-border bg-card p-5">
            <h3 className="font-display text-lg font-medium mb-4">Tren Penjualan</h3>
            {overTime.length === 0 ? <Empty /> : (
              <ResponsiveContainer width="100%" height={300}>
                <AreaChart data={overTime}>
                  <defs>
                    <linearGradient id="grad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#4338CA" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#4338CA" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" vertical={false} />
                  <XAxis dataKey="label" tick={{ fontSize: 12 }} stroke="#94A3B8" />
                  <YAxis tick={{ fontSize: 12 }} stroke="#94A3B8" tickFormatter={(v) => `${v / 1000}k`} />
                  <Tooltip formatter={(v) => rupiah(v)} />
                  <Area type="monotone" dataKey="total" stroke="#4338CA" strokeWidth={2} fill="url(#grad)" name="Penjualan" />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </div>

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <div className="rounded-lg border border-border bg-card p-5">
              <h3 className="font-display text-lg font-medium mb-4">Produk Terlaris</h3>
              {topProducts.length === 0 ? <Empty /> : (
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={topProducts.slice(0, 6)} layout="vertical" margin={{ left: 20 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" horizontal={false} />
                    <XAxis type="number" tick={{ fontSize: 12 }} stroke="#94A3B8" tickFormatter={(v) => `${v / 1000}k`} />
                    <YAxis type="category" dataKey="name" tick={{ fontSize: 12 }} stroke="#94A3B8" width={90} />
                    <Tooltip formatter={(v) => rupiah(v)} />
                    <Bar dataKey="revenue" radius={[0, 6, 6, 0]} name="Pendapatan">
                      {topProducts.slice(0, 6).map((_, i) => <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />)}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              )}
            </div>

            <div className="rounded-lg border border-border bg-card p-5">
              <h3 className="font-display text-lg font-medium mb-4">Penjualan per Kategori</h3>
              {byCategory.length === 0 ? <Empty /> : (
                <ResponsiveContainer width="100%" height={280}>
                  <PieChart>
                    <Pie data={byCategory} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={90} innerRadius={50} paddingAngle={2}>
                      {byCategory.map((_, i) => <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />)}
                    </Pie>
                    <Tooltip formatter={(v) => rupiah(v)} />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              )}
            </div>
          </div>

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <div className="rounded-lg border border-border bg-card p-5">
              <h3 className="font-display text-lg font-medium mb-4">Metode Pembayaran</h3>
              {payMethods.length === 0 ? <Empty /> : (
                <div className="space-y-3">
                  {payMethods.map((m, i) => (
                    <div key={m.key} className="flex items-center justify-between rounded-lg bg-secondary px-4 py-3">
                      <div className="flex items-center gap-3">
                        <span className="h-3 w-3 rounded-full" style={{ background: CHART_COLORS[i % CHART_COLORS.length] }} />
                        <span className="font-medium">{m.method}</span>
                        <span className="text-xs text-muted-foreground">({m.count} transaksi)</span>
                      </div>
                      <span className="font-semibold">{rupiah(m.total)}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="rounded-lg border border-border bg-card p-5">
              <h3 className="font-display text-lg font-medium mb-4 flex items-center gap-2"><AlertTriangle className="h-4 w-4 text-amber-500" /> Stok Menipis</h3>
              {lowStock.length === 0 ? (
                <p className="text-sm text-muted-foreground py-8 text-center">Semua stok aman</p>
              ) : (
                <div className="space-y-2">
                  {lowStock.map((p) => (
                    <div key={p.id} className="flex items-center justify-between rounded-lg border border-border px-4 py-2.5">
                      <span className="font-medium">{p.name}</span>
                      <span className={`text-sm font-semibold ${p.stock <= 0 ? "text-destructive" : "text-amber-600"}`}>Sisa {p.stock}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

const Empty = () => <p className="text-sm text-muted-foreground py-16 text-center">Belum ada data pada periode ini</p>;
