// Typer der matcher backendens API-kontrakter.
export interface CustomerMe {
  customer_id: string;
  customer_number: string;
  first_name: string;
  last_name: string;
  email: string;
}

export interface Account {
  id: string;
  account_number: string;
  account_type: string;
  balance: string;
  currency: string;
  status: string;
}

export interface Transaction {
  transfer_id: string;
  created_at: string;
  description: string | null;
  signed_amount: string;
  entry_type: string;
  counterpart_account: string | null;
}

export interface Transfer {
  id: string;
  sender_account_id: string | null;
  receiver_account_id: string;
  amount: string;
  status: string;
  description: string | null;
  created_at: string;
}

export interface Loan {
  id: string;
  amount: string;
  loan_type: string;
  duration_months: number;
  purpose: string;
  status: string;
  decision_note: string | null;
  created_at: string;
  reviewed_at: string | null;
}

export interface ApiError {
  code: string;
  message: string;
  request_id?: string;
}
