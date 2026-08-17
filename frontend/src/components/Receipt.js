import { rupiah } from "@/lib/api";

const methodLabel = { cash: "Tunai", card: "Kartu", qris: "QRIS" };

export default function Receipt({ sale, cashier }) {
  const date = new Date(sale.created_at);
  return (
    <div className="receipt-print rounded-lg border border-border bg-white p-4 text-sm text-slate-800" data-testid="receipt-content">
      <div className="text-center">
        <p className="font-display text-lg font-semibold">Mandiri POS</p>
        <p className="text-xs text-slate-500">Terima kasih atas kunjungan Anda</p>
      </div>
      <div className="my-3 border-t border-dashed border-slate-300" />
      <div className="flex justify-between text-xs text-slate-500">
        <span>{sale.receipt_no}</span>
        <span>{date.toLocaleString("id-ID")}</span>
      </div>
      <p className="text-xs text-slate-500">Kasir: {cashier || sale.cashier_name}</p>
      <div className="my-3 border-t border-dashed border-slate-300" />
      <div className="space-y-1.5">
        {sale.items.map((i, idx) => (
          <div key={idx} className="flex justify-between">
            <div className="min-w-0">
              <p className="truncate">{i.name}</p>
              <p className="text-xs text-slate-500">{i.qty} x {rupiah(i.price)}</p>
            </div>
            <span className="font-medium">{rupiah(i.price * i.qty)}</span>
          </div>
        ))}
      </div>
      <div className="my-3 border-t border-dashed border-slate-300" />
      <div className="space-y-1">
        <div className="flex justify-between text-slate-500">
          <span>Subtotal</span>
          <span>{rupiah(sale.subtotal)}</span>
        </div>
        {sale.discount > 0 && (
          <div className="flex justify-between text-slate-500">
            <span>Diskon</span>
            <span>- {rupiah(sale.discount)}</span>
          </div>
        )}
        <div className="flex justify-between font-semibold text-base pt-1">
          <span>Total</span>
          <span>{rupiah(sale.total)}</span>
        </div>
        <div className="flex justify-between text-slate-500">
          <span>Bayar ({methodLabel[sale.payment_method]})</span>
          <span>{rupiah(sale.amount_paid || sale.total)}</span>
        </div>
        {sale.payment_method === "cash" && (
          <div className="flex justify-between text-slate-500">
            <span>Kembalian</span>
            <span>{rupiah(sale.change)}</span>
          </div>
        )}
      </div>
      <div className="my-3 border-t border-dashed border-slate-300" />
      <p className="text-center text-xs text-slate-400">Struk ini adalah bukti pembayaran yang sah</p>
    </div>
  );
}
