import { useEffect, useState } from "react";
import api from "@/lib/api";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Bell, AlertTriangle } from "lucide-react";
import { toast } from "sonner";

export default function NotificationBell() {
  const [data, setData] = useState({ count: 0, items: [], threshold: 10 });

  useEffect(() => {
    api.get("/notifications").then((r) => {
      setData(r.data);
      if (r.data.count > 0) {
        toast.warning(`${r.data.count} produk stoknya menipis`, { description: "Cek lonceng notifikasi untuk detail." });
      }
    }).catch(() => {});
  }, []);

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button className="relative flex h-9 w-9 items-center justify-center rounded-lg border border-border bg-card transition-colors hover:bg-accent" data-testid="notification-bell">
          <Bell className="h-4 w-4" />
          {data.count > 0 && (
            <span className="absolute -right-1 -top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-destructive px-1 text-[10px] font-bold text-destructive-foreground" data-testid="notification-count">
              {data.count}
            </span>
          )}
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-72" data-testid="notification-dropdown">
        <div className="px-3 py-2 border-b border-border">
          <p className="text-sm font-semibold">Peringatan Stok</p>
          <p className="text-xs text-muted-foreground">Batas menipis: {data.threshold}</p>
        </div>
        {data.count === 0 ? (
          <p className="px-3 py-6 text-center text-sm text-muted-foreground">Semua stok aman 🎉</p>
        ) : (
          <div className="max-h-72 overflow-y-auto py-1">
            {data.items.map((it) => (
              <div key={it.id} className="flex items-center justify-between px-3 py-2 text-sm">
                <span className="flex items-center gap-2"><AlertTriangle className="h-3.5 w-3.5 text-amber-500" /> {it.name}</span>
                <span className={`font-semibold ${it.stock <= 0 ? "text-destructive" : "text-amber-600"}`}>Sisa {it.stock}</span>
              </div>
            ))}
          </div>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
