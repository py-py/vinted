const moneyFormat = new Intl.NumberFormat("pl-PL", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
})

export function formatMoney(amount: number | null | undefined, currency = "PLN"): string {
  if (amount == null) return "—"
  return `${moneyFormat.format(amount)} ${currency}`
}
