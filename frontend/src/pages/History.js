import { useEffect, useState } from "react";
import api, { rupiah } from "@/lib/api";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Receipt as ReceiptIcon, Loader2, Search, Printer, Banknote, CreditCard, QrCode } from "lucide-react";
import Receipt from "@/components/Receipt";
import { useSettings } from "@/lib/useSettings";

const methodIcon = { cash: Banknote, card: CreditCard, qris: QrCode };
const methodLabel = { cash: "Tunai", card: "Kartu", qris: "QRIS" };

export default function History() {
  const store = useSettings();
  const [sales, setSales] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState(null);

  useEffect(() => {
    api.get("/sales").then((r) => setSales(r.data)).finally(() => setLoading(false));
  }, []);

  const filtered = sales.filter((s) =>
    s.receipt_no.toLowerCase().includes(search.toLowerCase()) ||
    (s.cashier_name || "").toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="h-screen overflow-y-auto p-8">
      <div className="mb-6">
        <h1 className="font-display text-3xl font-semibold">Riwayat Transaksi</h1>
        <p className="text-sm text-muted-foreground mt-1">Semua transaksi penjualan</p>
      </div>

      <div className="relative mb-4 max-w-md">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input placeholder="Cari no. struk atau kasir..." value={search} onChange={(e) => setSearch(e.target.value)} className="pl-9" data-testid="history-search-input" />
      </div>

      {loading ? (
        <div className="flex h-64 items-center justify-center"><Loader2 className="h-6 w-6 animate-spin text-primary" /></div>
      ) : filtered.length === 0 ? (
        <div className="flex h-64 flex-col items-center justify-center text-muted-foreground rounded-lg border border-border bg-card">
          <ReceiptIcon className="h-10 w-10 mb-2 opacity-40" /><p>Belum ada transaksi</p>
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map((s) => {
            const Icon = methodIcon[s.payment_method] || Banknote;
            return (
              <button
                key={s.id}
                onClick={() => setSelected(s)}
                data-testid={`history-row-${s.id}`}
                className="flex w-full items-center justify-between rounded-lg border border-border bg-card p-4 text-left transition-transform duration-200 hover:-translate-y-0.5"
              >
                <div className="flex items-center gap-4">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-accent text-accent-foreground">
                    <Icon className="h-5 w-5" />
                  </div>
                  <div>
                    <p className="font-medium">{s.receipt_no}</p>
                    <p className="text-xs text-muted-foreground">
                      {new Date(s.created_at).toLocaleString("id-ID")} · {s.cashier_name} · {s.items.length} item
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="font-display font-semibold">{rupiah(s.total)}</p>
                  <p className="text-xs text-muted-foreground">{methodLabel[s.payment_method]}</p>
                </div>
              </button>
            );
          })}
        </div>
      )}

      <Dialog open={!!selected} onOpenChange={(o) => !o && setSelected(null)}>
        <DialogContent className="sm:max-w-sm" data-testid="history-receipt-dialog">
          <DialogHeader><DialogTitle className="font-display">Detail Transaksi</DialogTitle></DialogHeader>
          {selected && <Receipt sale={selected} store={store} />}
          <DialogFooter>
            <Button variant="outline" className="w-full" onClick={() => window.print()} data-testid="history-print-button">
              <Printer className="mr-2 h-4 w-4" /> Cetak Struk
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
