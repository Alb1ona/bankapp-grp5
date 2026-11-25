import { NavLink, useNavigate } from "react-router-dom";
import { ReactNode } from "react";
import { useAuth } from "../auth";
import { PERM, roleLabels } from "../types";
import DemoBanner from "./DemoBanner";

const BANK = (import.meta.env.VITE_BANK_NAME as string) || "Demobank";

export default function Layout({ children }: { children: ReactNode }) {
  const { employee, logout, can } = useAuth();
  const navigate = useNavigate();

  async function handleLogout() { await logout(); navigate("/login"); }

  return (
    <>
      <DemoBanner />
      <header className="topbar">
        <div className="brand"><span className="logo" />{BANK} · Intern</div>
        {employee && (
          // FR-16: kun menupunkter brugerens afdeling(er) giver adgang til.
          //   Kundesøgning   -> Kundeservice, Investering
          //   Lånebehandling -> Investering
          //   Auditlog       -> IT og drift  (systemstatus vises på Oversigt)
          <nav>
            <NavLink to="/" end>Oversigt</NavLink>
            {can(PERM.CUSTOMER_LOOKUP) && <NavLink to="/kunder">Kundesøgning</NavLink>}
            {can(PERM.LOAN_DECIDE) && <NavLink to="/laan">Lånebehandling</NavLink>}
            {can(PERM.AUDIT_READ) && <NavLink to="/audit">Auditlog</NavLink>}
          </nav>
        )}
        <div className="user">
          {employee && (
            <>
              <span>{employee.display_name} · {roleLabels(employee.roles) || "ingen afdeling"}</span>
              <button className="btn-ghost" onClick={handleLogout}>Log ud</button>
            </>
          )}
        </div>
      </header>
      <main className="container">{children}</main>
    </>
  );
}
