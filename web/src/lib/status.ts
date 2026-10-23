import type { SaleStatus } from "@/lib/api"

export const STATUS_ORDER: SaleStatus[] = [
  "none",
  "reserved",
  "wait_winter",
  "listed",
  "sold_unconfirmed",
  "sold",
  "parted_sold",
  "trash",
]

export const STATUSES: Record<SaleStatus, { label: string; className: string }> = {
  none: { label: "Not listed", className: "bg-muted text-muted-foreground" },
  listed: { label: "Listed", className: "bg-amber-500 text-white" },
  sold_unconfirmed: { label: "Sold (unconfirmed)", className: "bg-lime-500 text-white" },
  sold: { label: "SOLD", className: "bg-green-600 text-white" },
  reserved: { label: "Reserved", className: "bg-blue-600 text-white" },
  parted_sold: { label: "Parted Sold", className: "bg-teal-600 text-white" },
  wait_winter: { label: "Wait for winter", className: "bg-sky-500 text-white" },
  trash: { label: "Trash", className: "bg-rose-700 text-white" },
}
