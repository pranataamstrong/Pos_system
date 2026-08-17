import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "sonner";
import { AuthProvider, useAuth } from "@/context/AuthContext";
import Layout from "@/components/Layout";
import Login from "@/pages/Login";
import POS from "@/pages/POS";
import Products from "@/pages/Products";
import Categories from "@/pages/Categories";
import Users from "@/pages/Users";
import Reports from "@/pages/Reports";
import History from "@/pages/History";
import Settings from "@/pages/Settings";
import Customers from "@/pages/Customers";
import Shift from "@/pages/Shift";
import { Loader2 } from "lucide-react";

function ProtectedRoute({ children, adminOnly }) {
  const { user, loading } = useAuth();
  if (loading || user === null)
    return (
      <div className="flex h-screen items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  if (!user) return <Navigate to="/login" replace />;
  if (adminOnly && user.role !== "admin") return <Navigate to="/" replace />;
  return children;
}

function App() {
  return (
    <div className="App">
      <AuthProvider>
        <Toaster position="top-center" richColors />
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route
              path="/"
              element={
                <ProtectedRoute>
                  <Layout />
                </ProtectedRoute>
              }
            >
              <Route index element={<POS />} />
              <Route path="reports" element={<ProtectedRoute adminOnly><Reports /></ProtectedRoute>} />
              <Route path="products" element={<ProtectedRoute adminOnly><Products /></ProtectedRoute>} />
              <Route path="categories" element={<ProtectedRoute adminOnly><Categories /></ProtectedRoute>} />
              <Route path="users" element={<ProtectedRoute adminOnly><Users /></ProtectedRoute>} />
              <Route path="settings" element={<ProtectedRoute adminOnly><Settings /></ProtectedRoute>} />
              <Route path="customers" element={<Customers />} />
              <Route path="shift" element={<Shift />} />
              <Route path="history" element={<History />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </div>
  );
}

export default App;
