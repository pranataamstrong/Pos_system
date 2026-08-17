import { useEffect, useState } from "react";
import api, { formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog";
import { Plus, Pencil, Trash2, Tags, Loader2 } from "lucide-react";
import { toast } from "sonner";

const colors = ["#4338CA", "#10B981", "#F59E0B", "#0EA5E9", "#EC4899", "#8B5CF6", "#EF4444", "#14B8A6"];

export default function Categories() {
  const [cats, setCats] = useState([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [name, setName] = useState("");
  const [color, setColor] = useState(colors[0]);

  const load = async () => {
    setLoading(true);
    const { data } = await api.get("/categories");
    setCats(data);
    setLoading(false);
  };
  useEffect(() => { load(); }, []);

  const openNew = () => { setEditing(null); setName(""); setColor(colors[0]); setOpen(true); };
  const openEdit = (c) => { setEditing(c); setName(c.name); setColor(c.color || colors[0]); setOpen(true); };

  const save = async () => {
    if (!name) return toast.error("Nama kategori wajib diisi");
    try {
      if (editing) await api.put(`/categories/${editing.id}`, { name, color });
      else await api.post("/categories", { name, color });
      toast.success(editing ? "Kategori diperbarui" : "Kategori ditambahkan");
      setOpen(false);
      load();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
  };

  const remove = async (id) => {
    if (!window.confirm("Hapus kategori ini?")) return;
    await api.delete(`/categories/${id}`);
    toast.success("Kategori dihapus");
    load();
  };

  return (
    <div className="h-screen overflow-y-auto p-8">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="font-display text-3xl font-semibold">Kategori</h1>
          <p className="text-sm text-muted-foreground mt-1">Kelompokkan produk Anda</p>
        </div>
        <Button onClick={openNew} data-testid="add-category-button"><Plus className="mr-2 h-4 w-4" /> Tambah Kategori</Button>
      </div>

      {loading ? (
        <div className="flex h-64 items-center justify-center"><Loader2 className="h-6 w-6 animate-spin text-primary" /></div>
      ) : cats.length === 0 ? (
        <div className="flex h-64 flex-col items-center justify-center text-muted-foreground rounded-lg border border-border bg-card">
          <Tags className="h-10 w-10 mb-2 opacity-40" /><p>Belum ada kategori</p>
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
          {cats.map((c) => (
            <div key={c.id} className="group flex items-center justify-between rounded-lg border border-border bg-card p-4 transition-transform duration-200 hover:-translate-y-1" data-testid={`category-card-${c.id}`}>
              <div className="flex items-center gap-3 min-w-0">
                <span className="h-8 w-8 shrink-0 rounded-lg" style={{ background: c.color }} />
                <span className="truncate font-medium">{c.name}</span>
              </div>
              <div className="flex opacity-0 transition-opacity group-hover:opacity-100">
                <Button size="icon" variant="ghost" className="h-8 w-8" onClick={() => openEdit(c)} data-testid={`edit-category-${c.id}`}><Pencil className="h-4 w-4" /></Button>
                <Button size="icon" variant="ghost" className="h-8 w-8 text-destructive" onClick={() => remove(c.id)} data-testid={`delete-category-${c.id}`}><Trash2 className="h-4 w-4" /></Button>
              </div>
            </div>
          ))}
        </div>
      )}

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent data-testid="category-dialog">
          <DialogHeader><DialogTitle className="font-display">{editing ? "Edit Kategori" : "Tambah Kategori"}</DialogTitle></DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Nama Kategori</Label>
              <Input value={name} onChange={(e) => setName(e.target.value)} data-testid="category-name-input" />
            </div>
            <div className="space-y-2">
              <Label>Warna</Label>
              <div className="flex flex-wrap gap-2">
                {colors.map((c) => (
                  <button key={c} onClick={() => setColor(c)} style={{ background: c }} className={`h-9 w-9 rounded-lg transition-transform ${color === c ? "ring-2 ring-offset-2 ring-foreground scale-110" : ""}`} />
                ))}
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)}>Batal</Button>
            <Button onClick={save} data-testid="save-category-button">Simpan</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
