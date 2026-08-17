import { useEffect, useState } from "react";
import api, { rupiah, formatApiError } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Wallet, Loader2, LockOpen, Lock, ArrowDownRight, ArrowUpRight } from "lucide-react";
import { toast } from "sonner";

export default function Shift() {
  const { user } = useAuth();
  const [current, setCurrent] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [openDialog, setOpenDialog] = useState(false);
  const [closeDialog, setCloseDialog] = useState(false);
  const [openingCash, setOpeningCash] = useState("");
  const [countedCash, setCountedCash] = useState("");
  const [busy, setBusy] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const [c, h] = await Promise.all([api.get("/shifts/current"), api.get("/shifts")]);
      setCurrent(c.data);
      setHistory(h.data);
    } finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  const doOpen = async () => {
    setBusy(true);
    try {
      await api.post("/shifts/open", { opening_cash: Number(openingCash) || 0 });
      toast.success("Shift dibuka");
      setOpenDialog(false); setOpeningCash("");
      load();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
    finally { setBusy(false); }
  };

  const doClose = async () => {
    setBusy(true);
    try {
      const { data } = await api.post("/shifts/close", { counted_cash: Number(countedCash) || 0 });
      const diff = data.difference;
      toast.success(`Shift ditutup. Selisih: ${diff === 0 ? "Sesuai" : rupiah(diff)}`);
      setCloseDialog(false); setCountedCash("");
      load();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
    finally { setBusy(false); }
  };

  if (loading) return <div className="flex h-screen items-center justify-center"><Loader2 className="h-6 w-6 animate-spin text-primary" /></div>;

  return (
    <div className="h-screen overflow-y-auto p-8">
      <div className="mb-6">
        <h1 className="font-display text-3xl font-semibold">Shift Kasir</h1>
        <p className="text-sm text-muted-foreground mt-1">Buka & tutup kas untuk rekonsiliasi uang laci</p>
      </div>

      <div className="mb-8 rounded-lg border border-border bg-card p-6">
        {current ? (
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-emerald-100 text-emerald-600"><LockOpen className="h-6 w-6" /></div>
              <div>
                <p className="text-xs font-bold uppercase tracking-widest text-emerald-600">Shift Aktif</p>
                <p className="font-display text-lg font-semibold">Modal awal: {rupiah(current.opening_cash)}</p>
                <p className="text-sm text-muted-foreground">Dibuka {new Date(current.opened_at).toLocaleString("id-ID")} · {current.cashier_name}</p>
              </div>
            </div>
            <Button variant="destructive" onClick={() => setCloseDialog(true)} data-testid="close-shift-button">
              <Lock className="mr-2 h-4 w-4" /> Tutup Shift
            </Button>
          </div>
        ) : (
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-secondary text-muted-foreground"><Wallet className="h-6 w-6" /></div>
              <div>
                <p className="font-display text-lg font-semibold">Belum ada shift aktif</p>
                <p className="text-sm text-muted-foreground">Buka shift untuk mulai mencatat kas</p>
              </div>
            </div>
            <Button onClick={() => setOpenDialog(true)} data-testid="open-shift-button">
              <LockOpen className="mr-2 h-4 w-4" /> Buka Shift
            </Button>
          </div>
        )}
      </div>

      <h2 className="font-display text-lg font-medium mb-3">Riwayat Shift</h2>
      <div className="rounded-lg border border-border bg-card">
        {history.filter((s) => s.status === "closed").length === 0 ? (
          <p className="py-12 text-center text-sm text-muted-foreground">Belum ada shift yang ditutup</p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Kasir</TableHead>
                <TableHead>Dibuka</TableHead>
                <TableHead>Ditutup</TableHead>
                <TableHead className="text-right">Modal Awal</TableHead>
                <TableHead className="text-right">Penjualan Tunai</TableHead>
                <TableHead className="text-right">Kas Seharusnya</TableHead>
                <TableHead className="text-right">Dihitung</TableHead>
                <TableHead className="text-right">Selisih</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {history.filter((s) => s.status === "closed").map((s) => (
                <TableRow key={s.id} data-testid={`shift-row-${s.id}`}>
                  <TableCell className="font-medium">{s.cashier_name}</TableCell>
                  <TableCell className="text-muted-foreground text-xs">{new Date(s.opened_at).toLocaleString("id-ID")}</TableCell>
                  <TableCell className="text-muted-foreground text-xs">{s.closed_at ? new Date(s.closed_at).toLocaleString("id-ID") : "-"}</TableCell>
                  <TableCell className="text-right">{rupiah(s.opening_cash)}</TableCell>
                  <TableCell className="text-right">{rupiah(s.cash_sales)}</TableCell>
                  <TableCell className="text-right">{rupiah(s.expected_cash)}</TableCell>
                  <TableCell className="text-right">{rupiah(s.counted_cash)}</TableCell>
                  <TableCell className="text-right">
                    <span className={`inline-flex items-center gap-1 font-semibold ${s.difference === 0 ? "text-emerald-600" : s.difference > 0 ? "text-sky-600" : "text-destructive"}`}>
                      {s.difference > 0 ? <ArrowUpRight className="h-3 w-3" /> : s.difference < 0 ? <ArrowDownRight className="h-3 w-3" /> : null}
                      {rupiah(Math.abs(s.difference))}
                    </span>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </div>

      <Dialog open={openDialog} onOpenChange={setOpenDialog}>
        <DialogContent data-testid="open-shift-dialog">
          <DialogHeader><DialogTitle className="font-display">Buka Shift</DialogTitle></DialogHeader>
          <div className="space-y-2">
            <Label>Modal Awal / Uang Laci (Rp)</Label>
            <Input type="number" min="0" value={openingCash} onChange={(e) => setOpeningCash(e.target.value)} placeholder="0" data-testid="opening-cash-input" />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpenDialog(false)}>Batal</Button>
            <Button onClick={doOpen} disabled={busy} data-testid="confirm-open-shift">{busy ? <Loader2 className="h-4 w-4 animate-spin" /> : "Buka"}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={closeDialog} onOpenChange={setCloseDialog}>
        <DialogContent data-testid="close-shift-dialog">
          <DialogHeader><DialogTitle className="font-display">Tutup Shift</DialogTitle></DialogHeader>
          <div className="space-y-2">
            <Label>Uang di Laci Saat Ini (Rp)</Label>
            <Input type="number" min="0" value={countedCash} onChange={(e) => setCountedCash(e.target.value)} placeholder="0" data-testid="counted-cash-input" />
            <p className="text-xs text-muted-foreground">Sistem akan membandingkan dengan kas seharusnya (modal awal + penjualan tunai).</p>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCloseDialog(false)}>Batal</Button>
            <Button variant="destructive" onClick={doClose} disabled={busy} data-testid="confirm-close-shift">{busy ? <Loader2 className="h-4 w-4 animate-spin" /> : "Tutup Shift"}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
