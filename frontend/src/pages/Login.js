import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Store, Loader2 } from "lucide-react";
import { toast } from "sonner";

export default function Login() {
  const { login, user } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (user) navigate("/", { replace: true });
  }, [user, navigate]);

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await login(email, password);
      toast.success("Selamat datang!");
      navigate("/", { replace: true });
    } catch (err) {
      toast.error(formatApiError(err.response?.data?.detail) || "Gagal masuk");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen">
      <div className="hidden flex-1 flex-col justify-between bg-primary p-12 text-primary-foreground lg:flex">
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-white/15">
            <Store className="h-6 w-6" />
          </div>
          <span className="font-display text-xl font-semibold">Mandiri POS</span>
        </div>
        <div>
          <h1 className="font-display text-5xl font-semibold leading-tight tracking-tight">
            Kelola penjualan Anda dengan mudah.
          </h1>
          <p className="mt-6 max-w-md text-lg text-primary-foreground/80">
            Kasir cepat, kelola stok, dan laporan lengkap dalam satu aplikasi. Dibuat untuk bisnis Anda.
          </p>
        </div>
        <p className="text-sm text-primary-foreground/60">© 2026 Mandiri POS</p>
      </div>

      <div className="flex flex-1 items-center justify-center bg-background p-6">
        <form onSubmit={submit} className="w-full max-w-sm space-y-6 animate-fade-up">
          <div className="lg:hidden flex items-center gap-3 justify-center mb-2">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary text-primary-foreground">
              <Store className="h-5 w-5" />
            </div>
            <span className="font-display text-xl font-semibold">Mandiri POS</span>
          </div>
          <div>
            <h2 className="font-display text-2xl font-semibold">Masuk ke akun</h2>
            <p className="mt-1 text-sm text-muted-foreground">Masukkan email dan kata sandi Anda.</p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              type="email"
              placeholder="nama@email.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              data-testid="login-email-input"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="password">Kata Sandi</Label>
            <Input
              id="password"
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              data-testid="login-password-input"
            />
          </div>

          <Button type="submit" className="w-full" disabled={loading} data-testid="login-submit-button">
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : "Masuk"}
          </Button>
        </form>
      </div>
    </div>
  );
}
