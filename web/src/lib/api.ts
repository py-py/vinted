import type { components } from "@/types/api"

type Schemas = components["schemas"]
export type Item = Schemas["Item"]
export type Purchase = Schemas["Purchase"]
export type Sale = Schemas["Sale"]
export type SaleItem = Schemas["SaleItem"]
export type ItemsPage = Schemas["Page_Item_"]
export type SaleStatus = Schemas["SaleStatus"]
export type Stats = Schemas["Stats"]
export type Listing = Schemas["Listing"]
export type ListingPhoto = Schemas["ListingPhoto"]
export type ListingUpdate = Schemas["ListingUpdate"]

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, {
    ...init,
    // FormData sets its own multipart Content-Type (with the boundary).
    headers:
      init?.body instanceof FormData
        ? init.headers
        : { "Content-Type": "application/json", ...init?.headers },
  })
  if (!res.ok) throw new ApiError(res.status, `${res.status} ${res.statusText}`)
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

export type ItemsQuery = {
  status?: SaleStatus[]
  q?: string
  hasSellPrice?: boolean
  page?: number
  size?: number
}

export type PurchasesQuery = {
  q?: string
  dateFrom?: string
  dateTo?: string
}

export type SalesQuery = PurchasesQuery

export const api = {
  items({ status = [], q, hasSellPrice, page, size }: ItemsQuery): Promise<ItemsPage> {
    const params = new URLSearchParams()
    status.forEach((s) => params.append("status", s))
    if (q) params.set("q", q)
    if (hasSellPrice != null) params.set("has_sell_price", String(hasSellPrice))
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
  sales({ q, dateFrom, dateTo }: SalesQuery = {}): Promise<Sale[]> {
    const params = new URLSearchParams()
    if (q) params.set("q", q)
    if (dateFrom) params.set("date_from", dateFrom)
    if (dateTo) params.set("date_to", dateTo)
    return request(`/sales?${params}`)
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
  setSaleItem(txId: string, itemId: number, saleItemId: number | null) {
    return request(`/items/${txId}/${itemId}/sale`, {
      method: "PATCH",
      body: JSON.stringify({ sale_item_id: saleItemId }),
    })
  },
  setSellPrice(txId: string, itemId: number, sellPrice: number | null) {
    return request(`/items/${txId}/${itemId}/sell-price`, {
      method: "PATCH",
      body: JSON.stringify({ sell_price: sellPrice }),
    })
  },
  listings(): Promise<Listing[]> {
    return request("/listings")
  },
  listing(listingId: string): Promise<Listing> {
    return request(`/listings/${listingId}`)
  },
  createListing(): Promise<Listing> {
    return request("/listings", { method: "POST" })
  },
  updateListing(listingId: string, fields: ListingUpdate): Promise<Listing> {
    return request(`/listings/${listingId}`, { method: "PATCH", body: JSON.stringify(fields) })
  },
  deleteListing(listingId: string): Promise<void> {
    return request(`/listings/${listingId}`, { method: "DELETE" })
  },
  // One file per request: a batch is uploaded in parallel, under Cloud Run's request size limit.
  uploadListingPhoto(listingId: string, file: File): Promise<ListingPhoto> {
    const body = new FormData()
    body.append("file", file)
    return request(`/listings/${listingId}/photos`, { method: "POST", body })
  },
  // Swaps the photo for its edited version (rotated / cropped); the result has a new id.
  replaceListingPhoto(listingId: string, photoId: string, file: Blob): Promise<ListingPhoto> {
    const body = new FormData()
    body.append("file", file, "photo.jpg")
    return request(`/listings/${listingId}/photos/${photoId}`, { method: "PUT", body })
  },
  deleteListingPhoto(listingId: string, photoId: string): Promise<void> {
    return request(`/listings/${listingId}/photos/${photoId}`, { method: "DELETE" })
  },
  reorderListingPhotos(listingId: string, photoIds: string[]): Promise<ListingPhoto[]> {
    return request(`/listings/${listingId}/photos`, {
      method: "PATCH",
      body: JSON.stringify({ photo_ids: photoIds }),
    })
  },
}
