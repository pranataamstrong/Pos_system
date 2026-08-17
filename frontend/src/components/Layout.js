import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import {
  ShoppingCart,
  BarChart3,
  Package,
  Tags,
  Users as UsersIcon,
  Receipt,
  LogOut,
  Store,
  Settings as SettingsIcon,
  Wallet,
  UserRound,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import NotificationBell from "@/components/NotificationBell";

const navItems = [
  { to: "/", label: "Kasir", icon: ShoppingCart, end: true, admin: false },
  { to: "/reports", label: "Laporan", icon: BarChart3, admin: true },
  { to: "/products", label: "Produk", icon: Package, admin: true },
  { to: "/categories", label: "Kategori", icon: Tags, admin: true },
  { to: "/customers", label: "Pelanggan", icon: UserRound, admin: false },
  { to: "/shift", label: "Shift", icon: Wallet, admin: false },
  { to: "/history", label: "Riwayat", icon: Receipt, admin: false },
  { to: "/users", label: "Pengguna", icon: UsersIcon, admin: true },
  { to: "/settings", label: "Pengaturan", icon: SettingsIcon, admin: true },
];

export default function Layout() {
  const { user, logout } = useAuth();
  const isAdmin = user?.role === "admin";

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <aside className="flex w-64 flex-col border-r border-border bg-card">
        <div className="flex items-center justify-between px-6 py-6">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary text-primary-foreground">
              <Store className="h-5 w-5" />
            </div>
            <div>
              <p className="font-display text-lg font-semibold leading-none">Mandiri POS</p>
              <p className="text-xs text-muted-foreground mt-1">Point of Sale</p>
            </div>
          </div>
          <NotificationBell />
        </div>

        <nav className="flex-1 space-y-1 px-3 py-2">
          {navItems
            .filter((it) => !it.admin || isAdmin)
            .map((it) => (
              <NavLink
                key={it.to}
                to={it.to}
                end={it.end}
                data-testid={`nav-${it.label.toLowerCase()}`}
                className={({ isActive }) =>
                  `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors ${
                    isActive
                      ? "bg-primary text-primary-foreground"
                      : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                  }`
                }
              >
                <it.icon className="h-4 w-4" />
                {it.label}
              </NavLink>
            ))}
        </nav>

        <div className="border-t border-border p-4">
          <div className="mb-3 flex items-center gap-3 px-1">
            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-accent text-accent-foreground text-sm font-semibold">
              {(user?.name || "?").charAt(0).toUpperCase()}
            </div>
            <div className="min-w-0">
              <p className="truncate text-sm font-medium">{user?.name}</p>
              <p className="truncate text-xs text-muted-foreground capitalize">{user?.role === "admin" ? "Admin" : "Kasir"}</p>
            </div>
          </div>
          <Button
            variant="outline"
            size="sm"
            className="w-full justify-start gap-2"
            onClick={logout}
            data-testid="logout-button"
          >
            <LogOut className="h-4 w-4" />
            Keluar
          </Button>
        </div>
      </aside>

      <main className="flex-1 overflow-hidden">
        <Outlet />
      </main>
    </div>
  );
}
