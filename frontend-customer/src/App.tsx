import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth";
import Layout from "./components/Layout";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Accounts from "./pages/Accounts";
import Transactions from "./pages/Transactions";
import Transfer from "./pages/Transfer";
import Loans from "./pages/Loans";
import { ReactNode } from "react";

function Protected({ children }: { children: ReactNode }) {
  const { customer, loading } = useAuth();
  if (loading) return <Layout><p className="subtle">Indlæser…</p></Layout>;
  if (!customer) return <Navigate to="/login" replace />;
  return <Layout>{children}</Layout>;
}

export default function App() {
  const { customer } = useAuth();
  return (
    <Routes>
      <Route path="/login" element={customer ? <Navigate to="/" replace /> : <Login />} />
      <Route path="/" element={<Protected><Dashboard /></Protected>} />
      <Route path="/konti" element={<Protected><Accounts /></Protected>} />
      <Route path="/konti/:accountId" element={<Protected><Transactions /></Protected>} />
      <Route path="/overfoersel" element={<Protected><Transfer /></Protected>} />
      <Route path="/laan" element={<Protected><Loans /></Protected>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
