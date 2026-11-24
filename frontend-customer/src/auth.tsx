// Auth-kontekst for kundeportalen.
import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { api, setCsrfToken } from "./api";
import type { CustomerMe } from "./types";

interface AuthState {
  customer: CustomerMe | null;
  loading: boolean;
  login: (identifier: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [customer, setCustomer] = useState<CustomerMe | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Forsøg at genoprette session ved opstart (cookie findes måske).
    api.get<CustomerMe>("/api/v1/customer/auth/me")
      .then(setCustomer)
      .catch(() => setCustomer(null))
      .finally(() => setLoading(false));
  }, []);

  async function login(identifier: string, password: string) {
    const res = await api.post<{ csrf_token: string; customer: CustomerMe }>(
      "/api/v1/customer/auth/login",
      { identifier, password },
    );
    setCsrfToken(res.csrf_token);
    setCustomer(res.customer);
  }

  async function logout() {
    try {
      await api.post("/api/v1/customer/auth/logout");
    } finally {
      setCsrfToken(null);
      setCustomer(null);
    }
  }

  return (
    <AuthContext.Provider value={{ customer, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth skal bruges inde i AuthProvider");
  return ctx;
}
