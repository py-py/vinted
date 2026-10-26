import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { ImageOff, Loader2, Pencil, Plus, Sparkles, Trash2 } from "lucide-react"
import { useState } from "react"
import { Link, useNavigate } from "react-router"
import { toast } from "sonner"

import { PageHeader } from "@/components/shared/PageHeader"
import { PhotoGallery } from "@/components/shared/PhotoGallery"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
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
                <TableHead className="text-right">Actions</TableHead>
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
  const [galleryOpen, setGalleryOpen] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)
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
  const remove = useMutation({
    mutationFn: () => api.deleteListing(listing.id),
    onSuccess: () => {
      setConfirmDelete(false)
      queryClient.setQueryData<Listing[]>(["listings"], (old) =>
        old?.filter((l) => l.id !== listing.id),
      )
      queryClient.removeQueries({ queryKey: ["listings", listing.id] })
    },
    onError: () => toast.error("Failed to delete listing"),
  })
  const title = listing.title || "Untitled"
  const href = `/listings/${listing.id}`

  // Dialogs are siblings of the row, not children: React events bubble out of portals along the
  // component tree, so a click inside them would otherwise also open the listing.
  return (
    <>
      <TableRow className="cursor-pointer" onClick={() => navigate(href)}>
        <TableCell className="w-24">
          {main ? (
            <button
              type="button"
              className="block cursor-zoom-in"
              aria-label={`Preview photos of ${title}`}
              onClick={(e) => {
                e.stopPropagation()
                setGalleryOpen(true)
              }}
            >
              <img
                src={main.url}
                alt=""
                loading="lazy"
                decoding="async"
                className="size-20 rounded-md bg-muted object-cover"
              />
            </button>
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
            {title}
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
        <TableCell onClick={(e) => e.stopPropagation()}>
          <div className="flex justify-end gap-1">
            <Button
              variant="outline"
              size="sm"
              title="Send the photos to DeepSeek and save the title and description"
              disabled={listing.photos.length === 0 || analyze.isPending}
              onClick={() => analyze.mutate()}
            >
              {analyze.isPending ? <Loader2 className="animate-spin" /> : <Sparkles />}
              <span className="hidden sm:inline">Run analysis</span>
            </Button>
            <Button variant="ghost" size="icon-sm" asChild>
              <Link to={href} aria-label={`Edit ${title}`} title="Edit">
                <Pencil />
              </Link>
            </Button>
            <Button
              variant="ghost"
              size="icon-sm"
              aria-label={`Delete ${title}`}
              title="Delete"
              onClick={() => setConfirmDelete(true)}
            >
              <Trash2 />
            </Button>
          </div>
        </TableCell>
      </TableRow>

      {galleryOpen && (
        <PhotoGallery
          photos={listing.photos.map((p) => p.url)}
          fallbacks={[]}
          title={title}
          open
          onOpenChange={(open) => !open && setGalleryOpen(false)}
        />
      )}

      <Dialog open={confirmDelete} onOpenChange={setConfirmDelete}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete listing?</DialogTitle>
            <DialogDescription>
              "{title}" and its {listing.photos.length} photos are deleted from storage too. This
              can't be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <DialogClose asChild>
              <Button variant="outline">Cancel</Button>
            </DialogClose>
            <Button
              variant="destructive"
              disabled={remove.isPending}
              onClick={() => remove.mutate()}
            >
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
