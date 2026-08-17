import { useEffect, useMemo, useState } from "react";
import api, { rupiah, formatApiError } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  Search,
  Plus,
  Minus,
  Trash2,
  ShoppingCart,
  Loader2,
  Banknote,
  CreditCard,
  QrCode,
  Printer,
  CheckCircle2,
} from "lucide-react";
import { toast } from "sonner";
import Receipt from "@/components/Receipt";

export default function POS() {
  const { user } = useAuth();
  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [activeCat, setActiveCat] = useState("all");
  const [search, setSearch] = useState("");
  const [cart, setCart] = useState([]);
  const [loading, setLoading] = useState(true);

  const [payOpen, setPayOpen] = useState(false);
  const [method, setMethod] = useState("cash");
  const [amountPaid, setAmountPaid] = useState("");
  const [discount, setDiscount] = useState("");
  const [processing, setProcessing] = useState(false);
  const [lastSale, setLastSale] = useState(null);

  const load = async () => {
    setLoading(true);
    try {
      const [p, c] = await Promise.all([api.get("/products"), api.get("/categories")]);
      setProducts(p.data);
      setCategories(c.data);
    } catch (e) {
      toast.error("Gagal memuat data");
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => {
    load();
  }, []);

  const filtered = useMemo(() => {
    return products.filter((p) => {
      const matchCat = activeCat === "all" || p.category_id === activeCat;
      const matchSearch = p.name.toLowerCase().includes(search.toLowerCase());
      return matchCat && matchSearch;
    });
  }, [products, activeCat, search]);

  const addToCart = (p) => {
    setCart((prev) => {
      const ex = prev.find((i) => i.product_id === p.id);
      if (ex) return prev.map((i) => (i.product_id === p.id ? { ...i, qty: i.qty + 1 } : i));
      return [...prev, { product_id: p.id, name: p.name, price: p.price, cost: p.cost || 0, qty: 1 }];
    });
  };
  const changeQty = (id, delta) =>
    setCart((prev) =>
      prev
        .map((i) => (i.product_id === id ? { ...i, qty: i.qty + delta } : i))
        .filter((i) => i.qty > 0)
    );
  const removeItem = (id) => setCart((prev) => prev.filter((i) => i.product_id !== id));

  const subtotal = cart.reduce((s, i) => s + i.price * i.qty, 0);
  const disc = Number(discount) || 0;
  const total = Math.max(0, subtotal - disc);
  const change = method === "cash" ? Math.max(0, (Number(amountPaid) || 0) - total) : 0;

  const openPay = () => {
    if (cart.length === 0) return toast.error("Keranjang masih kosong");
    setMethod("cash");
    setAmountPaid("");
    setDiscount(discount);
    setPayOpen(true);
  };

  const confirmPay = async () => {
    if (method === "cash" && Number(amountPaid) < total)
      return toast.error("Jumlah bayar kurang dari total");
    setProcessing(true);
    try {
      const { data } = await api.post("/sales", {
        items: cart.map((i) => ({ ...i })),
        discount: disc,
        payment_method: method,
        amount_paid: method === "cash" ? Number(amountPaid) || total : total,
      });
      setLastSale(data);
      setCart([]);
      setDiscount("");
      setPayOpen(false);
      toast.success("Pembayaran berhasil!");
      load();
    } catch (e) {
      toast.error(formatApiError(e.response?.data?.detail));
    } finally {
      setProcessing(false);
    }
  };

  const quickCash = [total, 50000, 100000, 150000, 200000];

  return (
    <div className="flex h-screen">
      {/* Product area */}
      <div className="flex flex-1 flex-col overflow-hidden">
        <div className="border-b border-border bg-card px-6 py-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Cari produk..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9"
              data-testid="product-search-input"
            />
          </div>
          <div className="mt-4 flex gap-2 overflow-x-auto pb-1">
            <button
              onClick={() => setActiveCat("all")}
              data-testid="category-filter-all"
              className={`whitespace-nowrap rounded-full px-4 py-1.5 text-sm font-medium transition-colors ${
                activeCat === "all" ? "bg-primary text-primary-foreground" : "bg-secondary text-secondary-foreground hover:bg-accent"
              }`}
            >
              Semua
            </button>
            {categories.map((c) => (
              <button
                key={c.id}
                onClick={() => setActiveCat(c.id)}
                data-testid={`category-filter-${c.id}`}
                className={`whitespace-nowrap rounded-full px-4 py-1.5 text-sm font-medium transition-colors ${
                  activeCat === c.id ? "bg-primary text-primary-foreground" : "bg-secondary text-secondary-foreground hover:bg-accent"
                }`}
              >
                {c.name}
              </button>
            ))}
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-6">
          {loading ? (
            <div className="flex h-full items-center justify-center">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
          ) : filtered.length === 0 ? (
            <div className="flex h-full flex-col items-center justify-center text-muted-foreground">
              <ShoppingCart className="h-10 w-10 mb-2 opacity-40" />
              <p>Tidak ada produk. Tambahkan produk dulu.</p>
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
              {filtered.map((p, idx) => (
                <button
                  key={p.id}
                  onClick={() => addToCart(p)}
                  data-testid={`product-card-${p.id}`}
                  style={{ animationDelay: `${idx * 30}ms` }}
                  className="group animate-fade-up overflow-hidden rounded-lg border border-border bg-card text-left transition-transform duration-200 hover:-translate-y-1"
                >
                  <div className="aspect-square w-full overflow-hidden bg-secondary">
                    {p.image ? (
                      <img src={p.image} alt={p.name} className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105" />
                    ) : (
                      <div className="flex h-full items-center justify-center text-3xl font-display font-semibold text-muted-foreground/40">
                        {p.name.charAt(0)}
                      </div>
                    )}
                  </div>
                  <div className="p-3">
                    <p className="line-clamp-1 text-sm font-medium">{p.name}</p>
                    <div className="mt-1 flex items-center justify-between">
                      <span className="text-sm font-semibold text-primary">{rupiah(p.price)}</span>
                      <span className={`text-xs ${p.stock <= 0 ? "text-destructive" : "text-muted-foreground"}`}>
                        Stok {p.stock}
                      </span>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Cart panel */}
      <div className="flex w-[380px] flex-col border-l border-border bg-card">
        <div className="flex items-center justify-between border-b border-border px-5 py-4">
          <h2 className="font-display text-lg font-semibold">Keranjang</h2>
          {cart.length > 0 && (
            <button
              onClick={() => setCart([])}
              className="text-xs text-muted-foreground hover:text-destructive transition-colors"
              data-testid="clear-cart-button"
            >
              Kosongkan
            </button>
          )}
        </div>

        <div className="flex-1 overflow-y-auto px-5 py-3">
          {cart.length === 0 ? (
            <div className="flex h-full flex-col items-center justify-center text-muted-foreground">
              <ShoppingCart className="h-10 w-10 mb-2 opacity-30" />
              <p className="text-sm">Keranjang kosong</p>
              <p className="text-xs">Klik produk untuk menambahkan</p>
            </div>
          ) : (
            <div className="space-y-3">
              {cart.map((i) => (
                <div key={i.product_id} className="flex items-center gap-3" data-testid={`cart-item-${i.product_id}`}>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium">{i.name}</p>
                    <p className="text-xs text-muted-foreground">{rupiah(i.price)}</p>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <Button size="icon" variant="outline" className="h-7 w-7" onClick={() => changeQty(i.product_id, -1)} data-testid={`cart-minus-${i.product_id}`}>
                      <Minus className="h-3 w-3" />
                    </Button>
                    <span className="w-6 text-center text-sm font-medium">{i.qty}</span>
                    <Button size="icon" variant="outline" className="h-7 w-7" onClick={() => changeQty(i.product_id, 1)} data-testid={`cart-plus-${i.product_id}`}>
                      <Plus className="h-3 w-3" />
                    </Button>
                  </div>
                  <span className="w-20 text-right text-sm font-semibold">{rupiah(i.price * i.qty)}</span>
                  <button onClick={() => removeItem(i.product_id)} className="text-muted-foreground hover:text-destructive transition-colors">
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="border-t border-border p-5">
          <div className="mb-3 flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Total</span>
            <span className="font-display text-2xl font-semibold" data-testid="cart-total">{rupiah(subtotal)}</span>
          </div>
          <Button className="w-full" size="lg" onClick={openPay} disabled={cart.length === 0} data-testid="checkout-button">
            Bayar
          </Button>
        </div>
      </div>

      {/* Payment dialog */}
      <Dialog open={payOpen} onOpenChange={setPayOpen}>
        <DialogContent className="sm:max-w-md" data-testid="payment-dialog">
          <DialogHeader>
            <DialogTitle className="font-display">Pembayaran</DialogTitle>
          </DialogHeader>

          <div className="space-y-4">
            <div className="flex items-center justify-between rounded-lg bg-secondary px-4 py-3">
              <span className="text-sm text-muted-foreground">Total Tagihan</span>
              <span className="font-display text-xl font-semibold">{rupiah(total)}</span>
            </div>

            <div className="space-y-2">
              <Label>Diskon (Rp)</Label>
              <Input type="number" min="0" placeholder="0" value={discount} onChange={(e) => setDiscount(e.target.value)} data-testid="discount-input" />
            </div>

            <div className="space-y-2">
              <Label>Metode Pembayaran</Label>
              <div className="grid grid-cols-3 gap-2">
                {[
                  { k: "cash", label: "Tunai", icon: Banknote },
                  { k: "card", label: "Kartu", icon: CreditCard },
                  { k: "qris", label: "QRIS", icon: QrCode },
                ].map((m) => (
                  <button
                    key={m.k}
                    onClick={() => setMethod(m.k)}
                    data-testid={`payment-method-${m.k}`}
                    className={`flex flex-col items-center gap-1.5 rounded-lg border py-3 text-xs font-medium transition-colors ${
                      method === m.k ? "border-primary bg-accent text-accent-foreground" : "border-border hover:bg-secondary"
                    }`}
                  >
                    <m.icon className="h-5 w-5" />
                    {m.label}
                  </button>
                ))}
              </div>
            </div>

            {method === "cash" && (
              <div className="space-y-2">
                <Label>Jumlah Bayar</Label>
                <Input type="number" min="0" placeholder="0" value={amountPaid} onChange={(e) => setAmountPaid(e.target.value)} data-testid="amount-paid-input" />
                <div className="flex flex-wrap gap-2">
                  {quickCash.map((v, i) => (
                    <button key={i} onClick={() => setAmountPaid(String(v))} className="rounded-full bg-secondary px-3 py-1 text-xs hover:bg-accent transition-colors">
                      {i === 0 ? "Uang Pas" : rupiah(v)}
                    </button>
                  ))}
                </div>
                {Number(amountPaid) >= total && amountPaid !== "" && (
                  <div className="flex justify-between text-sm pt-1">
                    <span className="text-muted-foreground">Kembalian</span>
                    <span className="font-semibold text-emerald-600" data-testid="change-amount">{rupiah(change)}</span>
                  </div>
                )}
              </div>
            )}
          </div>

          <DialogFooter>
            <Button onClick={confirmPay} disabled={processing} className="w-full" size="lg" data-testid="confirm-payment-button">
              {processing ? <Loader2 className="h-4 w-4 animate-spin" /> : `Konfirmasi ${rupiah(total)}`}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Receipt dialog */}
      <Dialog open={!!lastSale} onOpenChange={(o) => !o && setLastSale(null)}>
        <DialogContent className="sm:max-w-sm" data-testid="receipt-dialog">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 font-display">
              <CheckCircle2 className="h-5 w-5 text-emerald-500" /> Transaksi Berhasil
            </DialogTitle>
          </DialogHeader>
          {lastSale && <Receipt sale={lastSale} cashier={user?.name} />}
          <DialogFooter className="flex-row gap-2">
            <Button variant="outline" className="flex-1" onClick={() => window.print()} data-testid="print-receipt-button">
              <Printer className="mr-2 h-4 w-4" /> Cetak
            </Button>
            <Button className="flex-1" onClick={() => setLastSale(null)} data-testid="new-transaction-button">
              Transaksi Baru
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
