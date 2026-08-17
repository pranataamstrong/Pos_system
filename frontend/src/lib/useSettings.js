import { useEffect, useState } from "react";
import api from "@/lib/api";

export function useSettings() {
  const [store, setStore] = useState(null);
  useEffect(() => {
    api.get("/settings").then((r) => setStore(r.data)).catch(() => setStore(null));
  }, []);
  return store;
}
