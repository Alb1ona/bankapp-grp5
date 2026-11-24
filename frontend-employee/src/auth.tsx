import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { api, setCsrfToken } from "./api";
import type { EmployeeMe } from "./types";

interface AuthState {
  employee: EmployeeMe | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  can: (perm: string) => boolean;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [employee, setEmployee] = useState<EmployeeMe | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get<EmployeeMe>("/api/v1/internal/auth/me")
      .then(setEmployee)
      .catch(() => setEmployee(null))
      .finally(() => setLoading(false));
  }, []);

  async function login(username: string, password: string) {
    const res = await api.post<{ csrf_token: string; employee: EmployeeMe }>(
      "/api/v1/internal/auth/login", { username, password });
    setCsrfToken(res.csrf_token);
    setEmployee(res.employee);
  }

  async function logout() {
    try { await api.post("/api/v1/internal/auth/logout"); }
    finally { setCsrfToken(null); setEmployee(null); }
  }

  function can(perm: string) {
    return !!employee && employee.permissions.includes(perm);
  }

  return (
    <AuthContext.Provider value={{ employee, loading, login, logout, can }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth skal bruges inde i AuthProvider");
  return ctx;
}
