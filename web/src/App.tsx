import { BrowserRouter, Route, Routes } from "react-router"

import { AdminLayout } from "@/components/layout/AdminLayout"
import { DashboardPage } from "@/pages/Dashboard"
import { ItemsPage } from "@/pages/Items"
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
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
