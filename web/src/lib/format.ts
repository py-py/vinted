export function formatMoney(amount: number | null | undefined, currency = "PLN"): string {
  if (amount == null) return "—"
  return `${amount.toFixed(2)} ${currency}`
}
