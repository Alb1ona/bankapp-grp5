export interface EmployeeMe {
  employee_id: string;
  ad_username: string;
  display_name: string;
  roles: string[];
  permissions: string[];
}

export interface CustomerSearchResult {
  customer_id: string;
  customer_number: string;
  full_name: string;
  email: string;
}

export interface AccountAdminView {
  id: string;
  account_number: string;
  account_type: string;
  balance: string;
  currency: string;
  status: string;
}

export interface LoanAdminView {
  id: string;
  customer_id: string;
  amount: string;
  loan_type: string;
  duration_months: number;
  purpose: string;
  status: string;
  decision_note: string | null;
  reviewed_by_employee_id: string | null;
  created_at: string;
  reviewed_at: string | null;
}

export interface AuditEventView {
  id: string;
  timestamp: string;
  actor_type: string | null;
  actor_id: string | null;
  event_type: string;
  severity: string;
  result: string;
  source_ip: string | null;
  target_type: string | null;
  target_id: string | null;
  request_id: string | null;
  reason: string | null;
}

// Rettigheder (matcher backendens Permission-enum).
export const PERM = {
  CUSTOMER_LOOKUP: "CUSTOMER_LOOKUP",
  LOAN_DECIDE: "LOAN_DECIDE",
  AUDIT_READ: "AUDIT_READ",
  SYSTEM_STATUS_READ: "SYSTEM_STATUS_READ",
} as const;

export interface ApiError {
  code: string;
  message: string;
  request_id?: string;
}
