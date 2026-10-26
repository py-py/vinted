const moneyFormat = new Intl.NumberFormat("pl-PL", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
})

export function formatMoney(amount: number | null | undefined, currency = "PLN"): string {
  if (amount == null) return "—"
  return `${moneyFormat.format(amount)} ${currency}`
}

// ISO-style "2026-10-26 11:20" in local time.
export function formatDateTime(value: string): string {
  const d = new Date(value)
  const pad = (n: number) => String(n).padStart(2, "0")
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}
