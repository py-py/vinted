import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { ImageOff, Loader2, Plus, Sparkles } from "lucide-react"
import { Link, useNavigate } from "react-router"
import { toast } from "sonner"

import { PageHeader } from "@/components/shared/PageHeader"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { api, type Listing } from "@/lib/api"
import { formatDateTime } from "@/lib/format"
import { cn } from "@/lib/utils"

export function ListingsPage() {
  const { data, isPending, isError, error } = useQuery({
    queryKey: ["listings"],
    queryFn: api.listings,
  })

  return (
    <div className="space-y-6">
      <PageHeader
        title="Listings"
        description={data ? `${data.length} listings` : "Photos for new Vinted listings"}
        actions={
          <Button asChild>
            <Link to="/listings/new">
              <Plus />
              Add new listing
            </Link>
          </Button>
        }
      />

      {isError ? (
        <p className="text-sm text-destructive">Failed to load listings: {error.message}</p>
      ) : isPending ? (
        <Skeleton className="h-96 w-full rounded-xl" />
      ) : data.length === 0 ? (
        <p className="text-sm text-muted-foreground">No listings yet.</p>
      ) : (
        <div className="rounded-xl border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-24" />
                <TableHead>Title</TableHead>
                <TableHead className="text-right">Photos</TableHead>
                <TableHead className="hidden sm:table-cell">Created</TableHead>
                <TableHead className="hidden md:table-cell">Updated</TableHead>
                <TableHead className="text-right">Analysis</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.map((listing) => (
                <ListingRow key={listing.id} listing={listing} />
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  )
}

function ListingRow({ listing }: { listing: Listing }) {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [main] = listing.photos
  const analyze = useMutation({
    mutationFn: () => api.analyzeListing(listing.id),
    onSuccess: (updated) => {
      queryClient.setQueryData<Listing[]>(["listings"], (old) =>
        old?.map((l) => (l.id === updated.id ? updated : l)),
      )
      queryClient.setQueryData(["listings", updated.id], updated)
      toast.success(`Saved: ${updated.title}`)
    },
    onError: () => toast.error("Analysis failed"),
  })
  const href = `/listings/${listing.id}`

  return (
    <TableRow className="cursor-pointer" onClick={() => navigate(href)}>
      <TableCell className="w-24">
        {main ? (
          <img
            src={main.url}
            alt=""
            loading="lazy"
            decoding="async"
            className="size-20 rounded-md bg-muted object-cover"
          />
        ) : (
          <div className="flex size-20 items-center justify-center rounded-md bg-muted text-muted-foreground">
            <ImageOff className="size-6" />
          </div>
        )}
      </TableCell>
      <TableCell className="max-w-64 min-w-40 whitespace-normal">
        <Link
          to={href}
          className={cn(
            "line-clamp-2 font-medium hover:underline",
            !listing.title && "text-muted-foreground italic",
          )}
          onClick={(e) => e.stopPropagation()}
        >
          {listing.title || "Untitled"}
        </Link>
        <div className="font-mono text-xs text-muted-foreground">{listing.id.slice(0, 8)}</div>
      </TableCell>
      <TableCell className="text-right tabular-nums">{listing.photos.length}</TableCell>
      <TableCell className="hidden whitespace-nowrap tabular-nums sm:table-cell">
        {formatDateTime(listing.created_at)}
      </TableCell>
      <TableCell className="hidden whitespace-nowrap tabular-nums md:table-cell">
        {formatDateTime(listing.updated_at)}
      </TableCell>
      <TableCell className="text-right">
        <Button
          variant="outline"
          size="sm"
          title="Send the photos to DeepSeek and save the title and description"
          disabled={listing.photos.length === 0 || analyze.isPending}
          onClick={(e) => {
            e.stopPropagation()
            analyze.mutate()
          }}
        >
          {analyze.isPending ? <Loader2 className="animate-spin" /> : <Sparkles />}
          <span className="hidden sm:inline">Run analysis</span>
        </Button>
      </TableCell>
    </TableRow>
  )
}
