// Formateringshjælpere (dansk).
export function kr(amount: string | number): string {
  const n = typeof amount === "string" ? parseFloat(amount) : amount;
  return new Intl.NumberFormat("da-DK", { style: "currency", currency: "DKK" }).format(n);
}

export function dato(iso: string): string {
  try {
    return new Intl.DateTimeFormat("da-DK", {
      day: "2-digit", month: "2-digit", year: "numeric",
      hour: "2-digit", minute: "2-digit",
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

export function kontotype(t: string): string {
  switch (t) {
    case "LOENKONTO": return "Lønkonto";
    case "OPSPARING": return "Opsparing";
    case "BUDGET": return "Budgetkonto";
    default: return t;
  }
}

export function randomKey(): string {
  // Idempotency-nøgle pr. overførselsforsøg.
  return "ui-" + crypto.randomUUID().replace(/-/g, "").slice(0, 24);
}
