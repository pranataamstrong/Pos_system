import api from "@/lib/api";

// Print via cloud backend to a network (IP) ESC/POS printer.
// NOTE: the printer must be reachable from the server. For a printer on your
// local LAN, run the app/print-bridge on the same network or expose the printer.
export async function printNetwork(saleId, ip, port) {
  if (!saleId) throw new Error("Struk belum tersedia");
  const { data } = await api.post(`/print/${saleId}/network`, {
    ip: ip || null,
    port: port ? Number(port) : null,
  });
  return data;
}

// Print via Web Bluetooth directly from the browser to a BLE ESC/POS printer.
export async function printBluetooth(saleId) {
  if (!saleId) throw new Error("Struk belum tersedia");
  if (!navigator.bluetooth)
    throw new Error("Browser tidak mendukung Web Bluetooth. Gunakan Chrome/Edge (Android/desktop).");

  const { data } = await api.get(`/print/${saleId}`);
  const bytes = Uint8Array.from(atob(data.data), (c) => c.charCodeAt(0));

  const SERVICE = 0x18f0; // common ESC/POS BLE service
  let device;
  try {
    device = await navigator.bluetooth.requestDevice({
      filters: [{ services: [SERVICE] }],
      optionalServices: [SERVICE, 0xff00, 0xffe0],
    });
  } catch (e) {
    device = await navigator.bluetooth.requestDevice({
      acceptAllDevices: true,
      optionalServices: [SERVICE, 0xff00, 0xffe0],
    });
  }

  const server = await device.gatt.connect();
  let ch;
  try {
    const svc = await server.getPrimaryService(SERVICE);
    const chars = await svc.getCharacteristics();
    ch = chars.find((c) => c.properties.write || c.properties.writeWithoutResponse) || chars[0];
  } catch (e) {
    const services = await server.getPrimaryServices();
    for (const s of services) {
      const chars = await s.getCharacteristics();
      const w = chars.find((c) => c.properties.write || c.properties.writeWithoutResponse);
      if (w) { ch = w; break; }
    }
  }
  if (!ch) {
    try { device.gatt.disconnect(); } catch (e) {}
    throw new Error("Karakteristik printer tidak ditemukan");
  }

  const CHUNK = 128;
  for (let i = 0; i < bytes.length; i += CHUNK) {
    const chunk = bytes.slice(i, i + CHUNK);
    if (ch.properties.writeWithoutResponse) await ch.writeValueWithoutResponse(chunk);
    else await ch.writeValue(chunk);
    await new Promise((r) => setTimeout(r, 20));
  }
  setTimeout(() => { try { device.gatt.disconnect(); } catch (e) {} }, 600);
}
