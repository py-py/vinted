import type { components } from "@/types/api"

type Schemas = components["schemas"]
export type Item = Schemas["Item"]
export type Purchase = Schemas["Purchase"]
export type Sale = Schemas["Sale"]
export type ItemsPage = Schemas["Page_Item_"]
export type SaleStatus = Schemas["SaleStatus"]
export type Stats = Schemas["Stats"]

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  // FormData bodies need the browser-generated multipart Content-Type (with boundary).
  const json = !(init?.body instanceof FormData)
  const res = await fetch(`/api${path}`, {
    ...init,
    headers: { ...(json && { "Content-Type": "application/json" }), ...init?.headers },
  })
  if (!res.ok) throw new ApiError(res.status, `${res.status} ${res.statusText}`)
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

export type ItemsQuery = {
  status?: SaleStatus[]
  q?: string
  page?: number
  size?: number
}

export type PurchasesQuery = {
  q?: string
  dateFrom?: string
  dateTo?: string
}

export type SaleInput = {
  title: string
  description: string
  pricePln?: number
  // In display order: an existing photo id (when editing) or a new resized JPEG.
  photos: (string | Blob)[]
}

function saleForm({ title, description, pricePln }: SaleInput): FormData {
  const body = new FormData()
  body.set("title", title)
  body.set("description", description)
  if (pricePln != null) body.set("price_pln", String(pricePln))
  return body
}

export const api = {
  items({ status = [], q, page, size }: ItemsQuery): Promise<ItemsPage> {
    const params = new URLSearchParams()
    status.forEach((s) => params.append("status", s))
    if (q) params.set("q", q)
    if (page) params.set("page", String(page))
    if (size) params.set("size", String(size))
    return request(`/items?${params}`)
  },
  purchases({ q, dateFrom, dateTo }: PurchasesQuery = {}): Promise<Purchase[]> {
    const params = new URLSearchParams()
    if (q) params.set("q", q)
    if (dateFrom) params.set("date_from", dateFrom)
    if (dateTo) params.set("date_to", dateTo)
    return request(`/purchases?${params}`)
  },
  stats(): Promise<Stats> {
    return request("/stats")
  },
  setStatus(txId: string, itemId: number, status: SaleStatus) {
    return request(`/items/${txId}/${itemId}`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    })
  },
  sales(): Promise<Sale[]> {
    return request("/sales")
  },
  createSale(input: SaleInput): Promise<Sale> {
    const body = saleForm(input)
    // A new sale has no existing photo ids, only Blobs.
    input.photos.forEach((photo, i) => body.append("photos", photo as Blob, `photo-${i + 1}.jpg`))
    return request("/sales", { method: "POST", body })
  },
  updateSale(id: string, input: SaleInput): Promise<Sale> {
    // `layout` is the final order; "new" takes the next file from `photos`.
    const body = saleForm(input)
    input.photos.forEach((photo, i) => {
      if (typeof photo === "string") {
        body.append("layout", photo)
      } else {
        body.append("layout", "new")
        body.append("photos", photo, `photo-${i + 1}.jpg`)
      }
    })
    return request(`/sales/${id}`, { method: "PUT", body })
  },
  deleteSale(id: string): Promise<void> {
    return request(`/sales/${id}`, { method: "DELETE" })
  },
}
