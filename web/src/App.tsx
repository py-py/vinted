import { BrowserRouter, Route, Routes } from "react-router"

import { AdminLayout } from "@/components/layout/AdminLayout"
import { DashboardPage } from "@/pages/Dashboard"
import { ItemsPage } from "@/pages/Items"
import { ListingEditPage } from "@/pages/ListingEdit"
import { ListingsPage } from "@/pages/Listings"
import { PurchasesPage } from "@/pages/Purchases"
import { SalesPage } from "@/pages/Sales"

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AdminLayout />}>
          <Route index element={<DashboardPage />} />
          <Route path="items" element={<ItemsPage />} />
          <Route path="purchases" element={<PurchasesPage />} />
          <Route path="sales" element={<SalesPage />} />
          <Route path="listings" element={<ListingsPage />} />
          <Route path="listings/new" element={<ListingEditPage />} />
          <Route path="listings/:listingId" element={<ListingEditPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
