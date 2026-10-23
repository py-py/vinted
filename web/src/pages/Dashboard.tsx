import { useQuery } from "@tanstack/react-query"
import { BadgeCheck, Package, Tag, Wallet } from "lucide-react"
import { Link } from "react-router"
import { Bar, BarChart, CartesianGrid, LabelList, XAxis, YAxis } from "recharts"

import { PageHeader } from "@/components/shared/PageHeader"
import { StatCard } from "@/components/shared/StatCard"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import {
  type ChartConfig,
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from "@/components/ui/chart"
import { Skeleton } from "@/components/ui/skeleton"
import { api, type Purchase, type SaleStatus, type Stats } from "@/lib/api"
import { formatMoney } from "@/lib/format"
import { STATUS_ORDER, STATUSES } from "@/lib/status"

const SOLD: SaleStatus[] = ["sold", "parted_sold"]
const ON_SALE: SaleStatus[] = ["listed", "reserved", "sold_unconfirmed"]
const MONTHS_SHOWN = 12

const spendConfig = {
  spent_pln: { label: "Spent", color: "var(--chart-2)" },
} satisfies ChartConfig

const statusConfig = {
  count: { label: "Items", color: "var(--chart-2)" },
} satisfies ChartConfig

function countOf(stats: Stats, statuses: SaleStatus[]): number {
  return statuses.reduce((sum, s) => sum + (stats.by_status[s] ?? 0), 0)
}

export function DashboardPage() {
  const stats = useQuery({ queryKey: ["stats"], queryFn: api.stats })
  const purchases = useQuery({ queryKey: ["purchases"], queryFn: () => api.purchases() })

  return (
    <div className="space-y-6">
      <PageHeader title="Dashboard" description="Purchases, spend and sale progress" />
      {stats.isError ? (
        <p className="text-sm text-destructive">Failed to load stats: {stats.error.message}</p>
      ) : stats.isPending ? (
        <DashboardSkeleton />
      ) : (
        <>
          <KpiRow stats={stats.data} />
          <div className="grid gap-4 lg:grid-cols-5">
            <SpendChart stats={stats.data} className="lg:col-span-3" />
            <StatusChart stats={stats.data} className="lg:col-span-2" />
          </div>
        </>
      )}
      <RecentPurchases purchases={purchases.data} isPending={purchases.isPending} />
    </div>
  )
}

function KpiRow({ stats }: { stats: Stats }) {
  const sold = countOf(stats, SOLD)
  const sellThrough = stats.items ? Math.round((sold / stats.items) * 100) : 0
  return (
    <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
      <StatCard
        title="Spent"
        value={`${Math.round(stats.spent_pln).toLocaleString("pl-PL")} PLN`}
        hint={`${stats.purchases} purchases`}
        icon={Wallet}
      />
      <StatCard
        title="Items"
        value={stats.items}
        hint={`${stats.by_status.none ?? 0} not listed`}
        icon={Package}
      />
      <StatCard
        title="On sale"
        value={countOf(stats, ON_SALE)}
        hint="Listed, reserved or awaiting confirmation"
        icon={Tag}
      />
      <StatCard title="Sold" value={sold} hint={`${sellThrough}% sell-through`} icon={BadgeCheck} />
    </div>
  )
}

function SpendChart({ stats, className }: { stats: Stats; className?: string }) {
  const data = stats.by_month.slice(-MONTHS_SHOWN).map((m) => ({
    ...m,
    spent_pln: Math.round(m.spent_pln),
  }))
  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle>Spend per month</CardTitle>
        <CardDescription>PLN incl. shipping and fees, last {MONTHS_SHOWN} months</CardDescription>
      </CardHeader>
      <CardContent>
        <ChartContainer config={spendConfig} className="aspect-auto h-64 w-full">
          <BarChart data={data} margin={{ left: 4, right: 4 }}>
            <CartesianGrid vertical={false} />
            <XAxis dataKey="month" tickLine={false} axisLine={false} tickMargin={8} />
            <YAxis tickLine={false} axisLine={false} width={40} />
            <ChartTooltip
              cursor={{ fillOpacity: 0.4 }}
              content={
                <ChartTooltipContent
                  formatter={(value, _name, item) => (
                    <div className="flex w-full justify-between gap-4">
                      <span className="text-muted-foreground">
                        {item.payload.items} items · {item.payload.purchases} orders
                      </span>
                      <span className="font-mono font-medium tabular-nums">{value} PLN</span>
                    </div>
                  )}
                />
              }
            />
            <Bar dataKey="spent_pln" fill="var(--color-spent_pln)" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ChartContainer>
      </CardContent>
    </Card>
  )
}

function StatusChart({ stats, className }: { stats: Stats; className?: string }) {
  const data = STATUS_ORDER.map((s) => ({
    status: STATUSES[s].label,
    count: stats.by_status[s] ?? 0,
  }))
  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle>Items by status</CardTitle>
        <CardDescription>{stats.items} items in total</CardDescription>
      </CardHeader>
      <CardContent>
        <ChartContainer config={statusConfig} className="aspect-auto h-64 w-full">
          <BarChart data={data} layout="vertical" margin={{ right: 32 }}>
            <XAxis type="number" hide />
            <YAxis
              type="category"
              dataKey="status"
              tickLine={false}
              axisLine={false}
              width={120}
            />
            <ChartTooltip cursor={{ fillOpacity: 0.4 }} content={<ChartTooltipContent />} />
            <Bar dataKey="count" fill="var(--color-count)" radius={[0, 4, 4, 0]}>
              <LabelList dataKey="count" position="right" className="fill-foreground" />
            </Bar>
          </BarChart>
        </ChartContainer>
      </CardContent>
    </Card>
  )
}

function RecentPurchases({
  purchases,
  isPending,
}: {
  purchases: Purchase[] | undefined
  isPending: boolean
}) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <div className="space-y-1.5">
          <CardTitle>Recent purchases</CardTitle>
          <CardDescription>Latest orders from Vinted</CardDescription>
        </div>
        <Link to="/purchases" className="text-sm text-muted-foreground hover:text-foreground">
          View all
        </Link>
      </CardHeader>
      <CardContent>
        {isPending ? (
          <Skeleton className="h-40 w-full" />
        ) : (
          <ul className="divide-y">
            {purchases?.slice(0, 6).map((p) => (
              <li key={p.tx_id}>
                <Link
                  to={`/purchases?tx=${p.tx_id}`}
                  className="-mx-2 flex items-center gap-3 rounded-md px-2 py-2 hover:bg-muted/50"
                >
                  <img
                    src={p.items[0]?.photo_urls[0]}
                    alt=""
                    className="size-10 shrink-0 rounded-md bg-muted object-cover"
                    referrerPolicy="no-referrer"
                  />
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-sm font-medium">
                      {p.items.map((i) => i.title).join(", ") || "—"}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {p.seller_login || "—"} · {p.order_date.slice(0, 10)} · {p.items.length}{" "}
                      {p.items.length === 1 ? "item" : "items"}
                    </div>
                  </div>
                  <div className="shrink-0 text-sm font-medium tabular-nums">
                    {formatMoney(p.total_price, p.currency)}
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  )
}

function DashboardSkeleton() {
  return (
    <>
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {Array.from({ length: 4 }, (_, i) => (
          <Skeleton key={i} className="h-28 rounded-xl" />
        ))}
      </div>
      <div className="grid gap-4 lg:grid-cols-5">
        <Skeleton className="h-80 rounded-xl lg:col-span-3" />
        <Skeleton className="h-80 rounded-xl lg:col-span-2" />
      </div>
    </>
  )
}
