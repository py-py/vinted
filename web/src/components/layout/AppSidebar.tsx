import { Camera, HandCoins, LayoutDashboard, Package, ShoppingBag } from "lucide-react"
import { NavLink } from "react-router"

import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
} from "@/components/ui/sidebar"

const NAV = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/purchases", label: "Purchases", icon: ShoppingBag },
  { to: "/items", label: "Purchase Items", icon: Package },
  { to: "/sales", label: "Sales", icon: HandCoins },
  { to: "/listings", label: "Listings", icon: Camera },
]

export function AppSidebar() {
  return (
    <Sidebar collapsible="icon">
      <SidebarHeader>
        <div className="flex h-8 items-center gap-2 px-2 font-semibold group-data-[collapsible=icon]:px-0">
          <span className="flex size-6 shrink-0 items-center justify-center rounded-md bg-primary text-xs text-primary-foreground">
            V
          </span>
          <span className="truncate group-data-[collapsible=icon]:hidden">Vinted admin</span>
        </div>
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupContent>
            <SidebarMenu>
              {NAV.map(({ to, label, icon: Icon }) => (
                <SidebarMenuItem key={to}>
                  {/* Prefix match, so /listings/:id keeps "Listings" active. */}
                  <NavLink to={to} end={to === "/"}>
                    {({ isActive }) => (
                      <SidebarMenuButton isActive={isActive} tooltip={label}>
                        <Icon />
                        <span>{label}</span>
                      </SidebarMenuButton>
                    )}
                  </NavLink>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
      <SidebarRail />
    </Sidebar>
  )
}
