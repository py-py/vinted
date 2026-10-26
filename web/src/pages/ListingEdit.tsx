import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { ArrowLeft, Sparkles, Trash2 } from "lucide-react"
import { lazy, Suspense, useEffect, useRef, useState } from "react"
import { Link, useNavigate, useParams } from "react-router"
import { toast } from "sonner"

import { ListingPhotoGrid } from "@/components/shared/ListingPhotoGrid"
import { PageHeader } from "@/components/shared/PageHeader"
import { PhotoGallery } from "@/components/shared/PhotoGallery"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Skeleton } from "@/components/ui/skeleton"
import { Textarea } from "@/components/ui/textarea"
import { api, ApiError, type Listing, type ListingPhoto, type ListingUpdate } from "@/lib/api"
import { formatDateTime } from "@/lib/format"

// cropperjs is only needed once a photo is edited.
const PhotoEditor = lazy(() =>
  import("@/components/shared/PhotoEditor").then((m) => ({ default: m.PhotoEditor })),
)

// Mirrors the backend guards in `vinted/listing/photos.py`; the backend re-checks the decoded file.
const MAX_FILE_SIZE = 25 * 1024 * 1024
// Extensions too: browsers often report HEIC with an empty MIME type.
const ACCEPT = "image/jpeg,image/png,image/webp,image/heic,image/heif,.heic,.heif"
const PARALLEL_UPLOADS = 4

function isAccepted(file: File) {
  return ACCEPT.split(",").some((t) =>
    t.startsWith(".") ? file.name.toLowerCase().endsWith(t) : file.type === t,
  )
}

function uploadError(error: unknown) {
  if (error instanceof ApiError && error.status === 413) return "larger than 25 MB"
  if (error instanceof ApiError && error.status === 422) return "not a supported image"
  return "upload failed"
}

// A photo in the unsaved draft; `edited` is the rotated / cropped JPEG, `url` its object URL.
type DraftPhoto = ListingPhoto & { edited?: Blob }

function revokeEdited(photos: DraftPhoto[]) {
  for (const p of photos) if (p.edited) URL.revokeObjectURL(p.url)
}

/**
 * Create (/listings/new) and edit (/listings/:listingId) page; both render the same form.
 * A new listing is created with the first upload or on Save, so leaving it empty creates nothing.
 * Uploads are stored right away; title, description, reorder, delete and rotate/crop stay a
 * local draft until Save.
 */
export function ListingEditPage() {
  const { listingId } = useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const queryKey = ["listings", listingId]

  const fileInput = useRef<HTMLInputElement>(null)
  const [pending, setPending] = useState(0)
  const [galleryIndex, setGalleryIndex] = useState<number | null>(null)
  const [editing, setEditing] = useState<DraftPhoto | null>(null)
  // null = no unsaved changes, the server's photos are shown.
  const [draft, setDraft] = useState<DraftPhoto[] | null>(null)
  // Same for title / description: null = unchanged.
  const [fields, setFields] = useState<ListingUpdate | null>(null)
  const [confirmDelete, setConfirmDelete] = useState(false)

  const { data: listing, isPending, isError, error } = useQuery({
    queryKey,
    queryFn: () => api.listing(listingId!),
    enabled: !!listingId,
  })
  const photos: DraftPhoto[] = draft ?? listing?.photos ?? []
  const title = fields?.title ?? listing?.title ?? ""
  const description = fields?.description ?? listing?.description ?? ""
  const changeFields = (update: ListingUpdate) => setFields({ title, description, ...update })
  const dirty = draft != null || fields != null
  const changePhotos = (update: (photos: DraftPhoto[]) => DraftPhoto[]) => setDraft(update(photos))

  // Closing the tab or reloading would lose the draft.
  useEffect(() => {
    if (!dirty) return
    const warn = (e: BeforeUnloadEvent) => e.preventDefault()
    window.addEventListener("beforeunload", warn)
    return () => window.removeEventListener("beforeunload", warn)
  }, [dirty])

  // Prefix match: refreshes this listing and the list page.
  const refetch = () => queryClient.invalidateQueries({ queryKey: ["listings"] })

  const save = useMutation({
    mutationFn: async ({ draft, fields }: { draft: DraftPhoto[] | null; fields: ListingUpdate | null }) => {
      // Title / description typed before any photo: Save creates the listing.
      const id = listingId ?? (await api.createListing()).id
      if (fields) await api.updateListing(id, fields)
      if (!draft) return
      const kept = new Set(draft.map((p) => p.id))
      // Edited photos come back with new ids, so replace first and reorder by the results.
      const saved = await Promise.all(
        draft.map((p) => (p.edited ? api.replaceListingPhoto(id, p.id, p.edited) : p)),
      )
      await Promise.all(
        (listing?.photos ?? [])
          .filter((p) => !kept.has(p.id))
          .map((p) => api.deleteListingPhoto(id, p.id)),
      )
      await api.reorderListingPhotos(
        id,
        saved.map((p) => p.id),
      )
    },
    onSuccess: (_, { draft }) => {
      if (draft) revokeEdited(draft)
      setDraft(null)
      setFields(null)
      void refetch()
      toast.success("Listing saved")
      navigate("/listings")
    },
    onError: () => {
      // Some steps may have gone through; show the server state, keep the draft to retry.
      toast.error("Failed to save listing")
      void refetch()
    },
  })
  // Fills the title / description draft; the user reviews it and saves.
  const fillFromPhotos = useMutation({
    mutationFn: (id: string) => api.describeListing(id),
    onSuccess: (text) => setFields(text),
    onError: () => toast.error("Couldn't describe the photos"),
  })
  const removeListing = useMutation({
    mutationFn: () => api.deleteListing(listingId!),
    onSuccess: () => {
      queryClient.removeQueries({ queryKey })
      void queryClient.invalidateQueries({ queryKey: ["listings"], exact: true })
      navigate("/listings")
    },
    onError: () => toast.error("Failed to delete listing"),
  })

  // On the create page the listing is created with the first upload, then the URL becomes
  // /listings/:id (same page component, so the uploads in flight carry on).
  async function upload(files: File[]) {
    const accepted = files.filter((f) => {
      const error = !isAccepted(f)
        ? "not a supported image"
        : f.size > MAX_FILE_SIZE
          ? "larger than 25 MB"
          : null
      if (error) toast.error(`${f.name}: ${error}`)
      return !error
    })
    if (accepted.length === 0) return

    // A new listing with nothing typed yet gets its title / description from the first photos.
    const autoFill = !listingId && !title && !description
    let id = listingId
    if (!id) {
      try {
        const created = await api.createListing()
        queryClient.setQueryData(["listings", created.id], created)
        id = created.id
        navigate(`/listings/${id}`, { replace: true })
      } catch {
        toast.error("Failed to create listing")
        return
      }
    }

    setPending((n) => n + accepted.length)
    const queue = [...accepted]
    let uploaded = 0
    const worker = async () => {
      for (let file = queue.shift(); file; file = queue.shift()) {
        try {
          const photo = await api.uploadListingPhoto(id, file)
          // Show each photo as soon as it's stored, in the saved list and in the draft.
          queryClient.setQueryData<Listing>(["listings", id], (old) =>
            old ? { ...old, photos: [...old.photos, photo] } : old,
          )
          setDraft((old) => old && [...old, photo])
          uploaded++
        } catch (e) {
          toast.error(`${file.name}: ${uploadError(e)}`)
        } finally {
          setPending((n) => n - 1)
        }
      }
    }
    await Promise.all(Array.from({ length: Math.min(PARALLEL_UPLOADS, accepted.length) }, worker))
    void queryClient.invalidateQueries({ queryKey: ["listings"], exact: true })
    if (autoFill && uploaded > 0) fillFromPhotos.mutate(id)
  }

  function cancel() {
    if (draft) revokeEdited(draft)
    navigate("/listings")
  }

  if (listingId && isError) {
    return <p className="text-sm text-destructive">Failed to load listing: {error.message}</p>
  }

  return (
    <div className="space-y-6">
      <Button variant="ghost" size="sm" className="-ml-2" asChild>
        <Link to="/listings">
          <ArrowLeft />
          Listings
        </Link>
      </Button>

      <PageHeader
        title={listingId ? "Edit listing" : "New listing"}
        description={
          listing
            ? `${listing.id.slice(0, 8)} · created ${formatDateTime(listing.created_at)}`
            : "Add photos to save the listing"
        }
        actions={
          listingId && (
            <Button variant="outline" onClick={() => setConfirmDelete(true)}>
              <Trash2 />
              Delete
            </Button>
          )
        }
      />

      <section className="space-y-3">
        <h2 className="text-lg font-medium">Photos</h2>
        <Card>
          <CardContent>
            {listingId && isPending ? (
              <Skeleton className="aspect-[5/1] w-full rounded-lg" />
            ) : (
              <ListingPhotoGrid
                photos={photos}
                onReorder={(ordered) => changePhotos(() => ordered)}
                onOpen={setGalleryIndex}
                onEdit={setEditing}
                onRemove={(photo) =>
                  changePhotos((old) => {
                    revokeEdited([photo])
                    return old.filter((p) => p.id !== photo.id)
                  })
                }
                pending={pending}
                onAdd={() => fileInput.current?.click()}
                onDropFiles={(files) => void upload(files)}
              />
            )}
            <input
              ref={fileInput}
              type="file"
              accept={ACCEPT}
              multiple
              hidden
              onChange={(e) => {
                void upload([...(e.target.files ?? [])])
                // Lets the same files be picked again.
                e.target.value = ""
              }}
            />
          </CardContent>
        </Card>
        <p className="text-xs text-muted-foreground">
          JPEG, PNG, WebP or HEIC, up to 25 MB each; stored at 1200 px max.
        </p>
      </section>

      <section className="space-y-3">
        <div className="flex items-center justify-between gap-2">
          <h2 className="text-lg font-medium">About your item</h2>
          <Button
            variant="outline"
            size="sm"
            onClick={() => fillFromPhotos.mutate(listingId!)}
            disabled={!listingId || photos.length === 0 || pending > 0 || fillFromPhotos.isPending}
          >
            <Sparkles />
            {fillFromPhotos.isPending ? "Writing…" : "Fill from photos"}
          </Button>
        </div>
        <Card>
          <CardContent className="grid gap-4 sm:grid-cols-[10rem_1fr] sm:items-start">
            <label htmlFor="listing-title" className="text-sm font-medium sm:pt-2">
              Title
            </label>
            <Input
              id="listing-title"
              value={title}
              onChange={(e) => changeFields({ title: e.target.value })}
              placeholder="e.g. Nike Sunray Protect sandals, size 27"
            />
            <label htmlFor="listing-description" className="text-sm font-medium sm:pt-2">
              Description
            </label>
            <Textarea
              id="listing-description"
              value={description}
              onChange={(e) => changeFields({ description: e.target.value })}
              placeholder="Tell buyers more about it"
              className="min-h-32"
            />
          </CardContent>
        </Card>
        <p className="text-xs text-muted-foreground">
          Both optional. "Fill from photos" asks DeepSeek for a draft from the saved photos.
        </p>
      </section>

      <div className="flex flex-wrap items-center justify-end gap-3">
        {dirty && <span className="mr-auto text-sm text-muted-foreground">Unsaved changes</span>}
        <Button variant="outline" onClick={cancel} disabled={save.isPending}>
          Cancel
        </Button>
        <Button
          onClick={() => (dirty ? save.mutate({ draft, fields }) : navigate("/listings"))}
          disabled={(!listingId && !dirty) || pending > 0 || save.isPending}
        >
          {save.isPending ? "Saving…" : "Save"}
        </Button>
      </div>

      {galleryIndex != null && (
        <PhotoGallery
          photos={photos.map((p) => p.url)}
          fallbacks={[]}
          title={listingId ? `Listing ${listingId.slice(0, 8)}` : "New listing"}
          initialIndex={galleryIndex}
          open
          onOpenChange={(open) => !open && setGalleryIndex(null)}
        />
      )}

      {editing && (
        <Suspense>
          <PhotoEditor
            key={editing.id}
            src={editing.url}
            onSave={(file) => {
              changePhotos((old) =>
                old.map((p) => {
                  if (p.id !== editing.id) return p
                  revokeEdited([p])
                  return { ...p, url: URL.createObjectURL(file), edited: file }
                }),
              )
              setEditing(null)
            }}
            onClose={() => setEditing(null)}
          />
        </Suspense>
      )}

      <Dialog open={confirmDelete} onOpenChange={setConfirmDelete}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete listing?</DialogTitle>
            <DialogDescription>
              Its {photos.length} photos are deleted from storage too. This can't be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <DialogClose asChild>
              <Button variant="outline">Cancel</Button>
            </DialogClose>
            <Button
              variant="destructive"
              disabled={removeListing.isPending}
              onClick={() => removeListing.mutate()}
            >
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
