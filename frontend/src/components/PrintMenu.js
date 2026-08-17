import { useState } from "react";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import { Printer, Bluetooth, Wifi, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { printBluetooth, printNetwork } from "@/lib/printer";

export default function PrintMenu({ saleId, className }) {
  const [busy, setBusy] = useState(false);

  const run = async (fn, okMsg) => {
    setBusy(true);
    try {
      await fn();
      toast.success(okMsg);
    } catch (e) {
      toast.error(e?.response?.data?.detail || e?.message || "Gagal mencetak");
    } finally {
      setBusy(false);
    }
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" className={className} disabled={busy} data-testid="print-menu-trigger">
          {busy ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Printer className="mr-2 h-4 w-4" />} Cetak
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" data-testid="print-menu">
        <DropdownMenuItem onClick={() => window.print()} data-testid="print-browser">
          <Printer className="mr-2 h-4 w-4" /> Browser / PDF
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => run(() => printBluetooth(saleId), "Struk terkirim via Bluetooth")} data-testid="print-bluetooth">
          <Bluetooth className="mr-2 h-4 w-4" /> Bluetooth (ESC/POS)
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => run(() => printNetwork(saleId), "Struk terkirim ke printer jaringan")} data-testid="print-network">
          <Wifi className="mr-2 h-4 w-4" /> Printer IP / Jaringan
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
