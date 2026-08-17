import { useEffect, useState } from "react";
import api, { formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Store, Loader2, Save } from "lucide-react";
import { toast } from "sonner";
import Receipt from "@/components/Receipt";

const sampleSale = {
  receipt_no: "INV-CONTOH-001",
  cashier_name: "Kasir",
  created_at: new Date().toISOString(),
  items: [
    { name: "Kopi Susu", price: 18000, qty: 1 },
    { name: "Croissant", price: 22000, qty: 2 },
  ],
  subtotal: 62000,
  discount: 2000,
  total: 60000,
  payment_method: "cash",
  amount_paid: 100000,
  change: 40000,
};

export default function Settings() {
  const [form, setForm] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.get("/settings").then((r) => setForm(r.data)).finally(() => setLoading(false));
  }, []);

  const save = async () => {
    setSaving(true);
    try {
      await api.put("/settings", form);
      toast.success("Pengaturan toko disimpan");
    } catch (e) {
      toast.error(formatApiError(e.response?.data?.detail));
    } finally {
      setSaving(false);
    }
  };

  if (loading || !form)
    return <div className="flex h-screen items-center justify-center"><Loader2 className="h-6 w-6 animate-spin text-primary" /></div>;

  return (
    <div className="h-screen overflow-y-auto p-8">
      <div className="mb-6 flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary text-primary-foreground"><Store className="h-5 w-5" /></div>
        <div>
          <h1 className="font-display text-3xl font-semibold">Pengaturan Toko</h1>
          <p className="text-sm text-muted-foreground mt-1">Informasi ini tampil di setiap struk</p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-8 lg:grid-cols-2">
        <div className="space-y-4 rounded-lg border border-border bg-card p-6">
          <div className="space-y-2">
            <Label>Nama Toko</Label>
            <Input value={form.store_name} onChange={(e) => setForm({ ...form, store_name: e.target.value })} data-testid="settings-name-input" />
          </div>
          <div className="space-y-2">
            <Label>Alamat</Label>
            <Textarea value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} data-testid="settings-address-input" />
          </div>
          <div className="space-y-2">
            <Label>Telepon</Label>
            <Input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} data-testid="settings-phone-input" />
          </div>
          <div className="space-y-2">
            <Label>URL Logo (opsional)</Label>
            <Input value={form.logo || ""} onChange={(e) => setForm({ ...form, logo: e.target.value })} placeholder="https://..." data-testid="settings-logo-input" />
          </div>
          <div className="space-y-2">
            <Label>Catatan Kaki Struk</Label>
            <Input value={form.footer} onChange={(e) => setForm({ ...form, footer: e.target.value })} data-testid="settings-footer-input" />
          </div>
          <Button onClick={save} disabled={saving} data-testid="save-settings-button">
            {saving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Save className="mr-2 h-4 w-4" />} Simpan
          </Button>
        </div>

        <div>
          <p className="mb-3 text-xs font-bold uppercase tracking-widest text-muted-foreground">Pratinjau Struk</p>
          <div className="max-w-xs">
            <Receipt sale={sampleSale} store={form} />
          </div>
        </div>
      </div>
    </div>
  );
}
