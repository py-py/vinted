import { BrowserRouter, Route, Routes } from "react-router"

import { AdminLayout } from "@/components/layout/AdminLayout"
import { ItemsPage } from "@/pages/Items"
import { PlaceholderPage } from "@/pages/Placeholder"

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AdminLayout />}>
          <Route index element={<PlaceholderPage title="Dashboard" />} />
          <Route path="items" element={<ItemsPage />} />
          <Route path="purchases" element={<PlaceholderPage title="Purchases" />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
