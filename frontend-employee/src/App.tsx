import { Navigate, Route, Routes } from "react-router-dom";
import { ReactNode } from "react";
import { useAuth } from "./auth";
import Layout from "./components/Layout";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import CustomerSearch from "./pages/CustomerSearch";
import LoanProcessing from "./pages/LoanProcessing";
import Audit from "./pages/Audit";

function Protected({ children, perm }: { children: ReactNode; perm?: string }) {
  const { employee, loading, can } = useAuth();
  if (loading) return <Layout><p className="subtle">Indlæser…</p></Layout>;
  if (!employee) return <Navigate to="/login" replace />;
  if (perm && !can(perm)) {
    return <Layout><div className="alert error">Du har ikke adgang til denne side.</div></Layout>;
  }
  return <Layout>{children}</Layout>;
}

export default function App() {
  const { employee } = useAuth();
  return (
    <Routes>
      <Route path="/login" element={employee ? <Navigate to="/" replace /> : <Login />} />
      <Route path="/" element={<Protected><Dashboard /></Protected>} />
      <Route path="/kunder" element={<Protected perm="CUSTOMER_LOOKUP"><CustomerSearch /></Protected>} />
      <Route path="/laan" element={<Protected perm="LOAN_DECIDE"><LoanProcessing /></Protected>} />
      <Route path="/audit" element={<Protected perm="AUDIT_READ"><Audit /></Protected>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
