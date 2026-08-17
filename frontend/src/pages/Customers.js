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
import { Plus, Pencil, Trash2, Users as UsersIcon, Loader2, Search, Star } from "lucide-react";
import { toast } from "sonner";

const empty = { name: "", phone: "", email: "" };

export default function Customers() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const [customers, setCustomers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(empty);

  const load = async () => {
    setLoading(true);
    const { data } = await api.get("/customers");
    setCustomers(data);
    setLoading(false);
  };
  useEffect(() => { load(); }, []);

  const openNew = () => { setEditing(null); setForm(empty); setOpen(true); };
  const openEdit = (c) => { setEditing(c); setForm({ name: c.name, phone: c.phone || "", email: c.email || "" }); setOpen(true); };

  const save = async () => {
    if (!form.name) return toast.error("Nama wajib diisi");
    try {
      if (editing) await api.put(`/customers/${editing.id}`, form);
      else await api.post("/customers", form);
      toast.success(editing ? "Pelanggan diperbarui" : "Pelanggan ditambahkan");
      setOpen(false);
      load();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
  };

  const remove = async (id) => {
    if (!window.confirm("Hapus pelanggan ini?")) return;
    await api.delete(`/customers/${id}`);
    toast.success("Pelanggan dihapus");
    load();
  };

  const filtered = customers.filter((c) =>
    c.name.toLowerCase().includes(search.toLowerCase()) || (c.phone || "").includes(search)
  );

  return (
    <div className="h-screen overflow-y-auto p-8">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="font-display text-3xl font-semibold">Pelanggan</h1>
          <p className="text-sm text-muted-foreground mt-1">Data pelanggan & poin loyalitas (1 poin / Rp 1.000)</p>
        </div>
        <Button onClick={openNew} data-testid="add-customer-button"><Plus className="mr-2 h-4 w-4" /> Tambah Pelanggan</Button>
      </div>

      <div className="relative mb-4 max-w-md">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input placeholder="Cari nama atau telepon..." value={search} onChange={(e) => setSearch(e.target.value)} className="pl-9" data-testid="customer-search-input" />
      </div>

      <div className="rounded-lg border border-border bg-card">
        {loading ? (
          <div className="flex h-64 items-center justify-center"><Loader2 className="h-6 w-6 animate-spin text-primary" /></div>
        ) : filtered.length === 0 ? (
          <div className="flex h-64 flex-col items-center justify-center text-muted-foreground">
            <UsersIcon className="h-10 w-10 mb-2 opacity-40" /><p>Belum ada pelanggan</p>
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Nama</TableHead>
                <TableHead>Telepon</TableHead>
                <TableHead className="text-right">Total Belanja</TableHead>
                <TableHead className="text-right">Poin</TableHead>
                <TableHead className="text-right">Aksi</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.map((c) => (
                <TableRow key={c.id} data-testid={`customer-row-${c.id}`}>
                  <TableCell className="font-medium">{c.name}</TableCell>
                  <TableCell className="text-muted-foreground">{c.phone || "-"}</TableCell>
                  <TableCell className="text-right">{rupiah(c.total_spent || 0)}</TableCell>
                  <TableCell className="text-right">
                    <span className="inline-flex items-center gap-1 font-semibold text-indigo-600"><Star className="h-3.5 w-3.5 fill-indigo-600" /> {c.points || 0}</span>
                  </TableCell>
                  <TableCell className="text-right">
                    {isAdmin && <Button size="icon" variant="ghost" className="h-8 w-8" onClick={() => openEdit(c)} data-testid={`edit-customer-${c.id}`}><Pencil className="h-4 w-4" /></Button>}
                    {isAdmin && <Button size="icon" variant="ghost" className="h-8 w-8 text-destructive" onClick={() => remove(c.id)} data-testid={`delete-customer-${c.id}`}><Trash2 className="h-4 w-4" /></Button>}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </div>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent data-testid="customer-dialog">
          <DialogHeader><DialogTitle className="font-display">{editing ? "Edit Pelanggan" : "Tambah Pelanggan"}</DialogTitle></DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2"><Label>Nama</Label><Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} data-testid="customer-name-input" /></div>
            <div className="space-y-2"><Label>Telepon</Label><Input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} data-testid="customer-phone-input" /></div>
            <div className="space-y-2"><Label>Email (opsional)</Label><Input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)}>Batal</Button>
            <Button onClick={save} data-testid="save-customer-button">Simpan</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
