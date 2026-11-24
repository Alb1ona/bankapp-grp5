import { NavLink, useNavigate } from "react-router-dom";
import { ReactNode } from "react";
import { useAuth } from "../auth";
import DemoBanner from "./DemoBanner";

const BANK = (import.meta.env.VITE_BANK_NAME as string) || "Demobank";

export default function Layout({ children }: { children: ReactNode }) {
  const { customer, logout } = useAuth();
  const navigate = useNavigate();

  async function handleLogout() {
    await logout();
    navigate("/login");
  }

  return (
    <>
      <DemoBanner />
      <header className="topbar">
        <div className="brand"><span className="logo" />{BANK}</div>
        {customer && (
          <nav>
            <NavLink to="/" end>Overblik</NavLink>
            <NavLink to="/konti">Konti</NavLink>
            <NavLink to="/overfoersel">Overførsel</NavLink>
            <NavLink to="/laan">Lån</NavLink>
          </nav>
        )}
        <div className="user">
          {customer && (
            <>
              <span>{customer.first_name} {customer.last_name}</span>
              <button className="btn-ghost" onClick={handleLogout}>Log ud</button>
            </>
          )}
        </div>
      </header>
      <main className="container">{children}</main>
    </>
  );
}
