export type SaleStatus =
  | 'none'
  | 'reserved'
  | 'wait_winter'
  | 'listed'
  | 'bought'
  | 'sold'
  | 'parted_sold'

export interface Item {
  id: number
  title: string
  size: string
  condition: string
  url: string
  catalog_id: number | null
  photo_url: string
  photo_urls: string[]
  paid_price: number | null
  listed_price: number | null
  price_pln: number | null
  currency: string
  is_deleted: boolean
  _sale_status: SaleStatus
}

export interface Purchase {
  tx_id: string
  seller_id: number | null
  seller_login: string
  seller_country: string
  order_date: string
  conversation_id: number | null
  total_price: number | null
  currency: string
  items: Item[]
}
