import { useMutation, useQueryClient } from "@tanstack/react-query"
import { ChevronLeft, ChevronRight, ImagePlus, Loader2, X } from "lucide-react"
import { useState, type DragEvent } from "react"
import { toast } from "sonner"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { api, type Sale, type SaleInput } from "@/lib/api"
import { MAX_PHOTO_SIDE, resizeImage } from "@/lib/image"
import { cn } from "@/lib/utils"

// Mirrors MAX_SALE_PHOTOS in vinted/admin/api.py (and Vinted's own limit).
const MAX_PHOTOS = 20

// A photo already stored for the sale (`id`) or a new resized one (`blob`, object URL).
type Photo = { key: string; url: string; id?: string; blob?: Blob }

type Props = {
  // Edit this sale; create a new one when omitted.
  sale?: Sale
  onClose: () => void
}

/** Mount only while open: state is initialised from `sale` once. */
export function SaleDialog({ sale, onClose }: Props) {
  const queryClient = useQueryClient()
  const [step, setStep] = useState<"photos" | "details">(sale ? "details" : "photos")
  const [photos, setPhotos] = useState<Photo[]>(
    () => sale?.photo_ids.map((id, i) => ({ key: id, id, url: sale.photo_urls[i] })) ?? [],
  )
  const [resizing, setResizing] = useState(0)
  const [title, setTitle] = useState(sale?.title ?? "")
  const [description, setDescription] = useState(sale?.description ?? "")
  const [price, setPrice] = useState(sale?.price_pln != null ? String(sale.price_pln) : "")

  const close = () => {
    photos.forEach((p) => p.blob && URL.revokeObjectURL(p.url))
    onClose()
  }

  const mutation = useMutation({
    mutationFn: () => {
      const input: SaleInput = {
        title: title.trim(),
        description: description.trim(),
        pricePln: price ? Number(price) : undefined,
        photos: photos.map((p) => p.id ?? p.blob!),
      }
      return sale ? api.updateSale(sale.id, input) : api.createSale(input)
    },
    onSuccess: () => {
      toast.success(sale ? "Sale updated" : "Sale created")
      queryClient.invalidateQueries({ queryKey: ["sales"] })
      close()
    },
    onError: () => toast.error(sale ? "Failed to update sale" : "Failed to create sale"),
  })

  const addFiles = async (files: File[]) => {
    const images = files.filter((f) => f.type.startsWith("image/"))
    const room = MAX_PHOTOS - photos.length
    if (images.length > room) toast.warning(`Only ${MAX_PHOTOS} photos per sale`)
    const batch = images.slice(0, Math.max(0, room))

    setResizing((n) => n + batch.length)
    const results = await Promise.allSettled(batch.map((f) => resizeImage(f)))
    setResizing((n) => n - batch.length)

    const added: Photo[] = []
    results.forEach((r, i) => {
      if (r.status === "fulfilled") {
        const url = URL.createObjectURL(r.value)
        added.push({ key: crypto.randomUUID(), blob: r.value, url })
      } else {
        toast.error(`Can't read ${batch[i].name}`)
      }
    })
    setPhotos((prev) => [...prev, ...added])
  }

  const remove = (key: string) =>
    setPhotos((prev) => {
      const photo = prev.find((p) => p.key === key)
      if (photo?.blob) URL.revokeObjectURL(photo.url)
      return prev.filter((p) => p.key !== key)
    })

  const move = (index: number, delta: number) =>
    setPhotos((prev) => {
      const next = [...prev]
      ;[next[index], next[index + delta]] = [next[index + delta], next[index]]
      return next
    })

  const onDrop = (e: DragEvent) => {
    e.preventDefault()
    addFiles([...e.dataTransfer.files])
  }

  const canSave =
    title.trim() !== "" && photos.length > 0 && resizing === 0 && !mutation.isPending

  return (
    <Dialog open onOpenChange={(open) => !open && close()}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>{sale ? "Edit sale" : "New sale"}</DialogTitle>
          <DialogDescription>
            {step === "photos"
              ? `Step 1 of 2 · Photos are resized to ${MAX_PHOTO_SIDE}px on the longest side`
              : "Step 2 of 2 · Title and description"}
          </DialogDescription>
        </DialogHeader>

        {step === "photos" ? (
          <div className="space-y-4">
            <label
              className="flex cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border border-dashed p-8 text-center text-sm text-muted-foreground transition-colors hover:bg-muted/50"
              onDragOver={(e) => e.preventDefault()}
              onDrop={onDrop}
            >
              <ImagePlus className="size-8" />
              <span>
                <span className="font-medium text-foreground">Choose photos</span> or drop them
                here
              </span>
              <span className="text-xs">
                {photos.length}/{MAX_PHOTOS} · the first photo is the cover
              </span>
              <input
                type="file"
                accept="image/*"
                multiple
                className="sr-only"
                onChange={(e) => {
                  addFiles([...(e.target.files ?? [])])
                  e.target.value = ""
                }}
              />
            </label>

            {(photos.length > 0 || resizing > 0) && (
              <ul className="grid grid-cols-3 gap-2 sm:grid-cols-4">
                {photos.map((p, i) => (
                  <li key={p.key} className="relative">
                    <img
                      src={p.url}
                      alt={`Photo ${i + 1}`}
                      className="aspect-square w-full rounded-md bg-muted object-cover"
                    />
                    {i === 0 && <Badge className="absolute top-1 left-1">Cover</Badge>}
                    <Button
                      variant="secondary"
                      size="icon-xs"
                      className="absolute top-1 right-1"
                      aria-label={`Remove photo ${i + 1}`}
                      onClick={() => remove(p.key)}
                    >
                      <X />
                    </Button>
                    <div className="absolute inset-x-1 bottom-1 flex justify-between">
                      <Button
                        variant="secondary"
                        size="icon-xs"
                        aria-label="Move left"
                        className={cn(i === 0 && "invisible")}
                        onClick={() => move(i, -1)}
                      >
                        <ChevronLeft />
                      </Button>
                      <Button
                        variant="secondary"
                        size="icon-xs"
                        aria-label="Move right"
                        className={cn(i === photos.length - 1 && "invisible")}
                        onClick={() => move(i, 1)}
                      >
                        <ChevronRight />
                      </Button>
                    </div>
                  </li>
                ))}
                {Array.from({ length: resizing }, (_, i) => (
                  <li
                    key={`resizing-${i}`}
                    className="flex aspect-square items-center justify-center rounded-md bg-muted"
                  >
                    <Loader2 className="size-5 animate-spin text-muted-foreground" />
                  </li>
                ))}
              </ul>
            )}
          </div>
        ) : (
          <div className="space-y-4">
            <button
              type="button"
              className="flex w-full gap-2 overflow-x-auto rounded-md text-left"
              title="Edit photos"
              onClick={() => setStep("photos")}
            >
              {photos.map((p) => (
                <img
                  key={p.key}
                  src={p.url}
                  alt=""
                  className="size-16 shrink-0 rounded-md bg-muted object-cover"
                />
              ))}
            </button>
            <div className="space-y-2">
              <Label htmlFor="sale-title">Title</Label>
              <Input
                id="sale-title"
                value={title}
                maxLength={100}
                placeholder="Nike Dunk Low, size 42"
                autoFocus
                onChange={(e) => setTitle(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="sale-description">Description</Label>
              <Textarea
                id="sale-description"
                value={description}
                maxLength={5000}
                rows={6}
                placeholder="Condition, measurements, flaws…"
                onChange={(e) => setDescription(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="sale-price">Price, PLN</Label>
              <Input
                id="sale-price"
                type="number"
                inputMode="decimal"
                min={0.01}
                step={0.01}
                className="sm:w-40"
                value={price}
                onChange={(e) => setPrice(e.target.value)}
              />
            </div>
          </div>
        )}

        <DialogFooter>
          {step === "photos" ? (
            <Button
              disabled={photos.length === 0 || resizing > 0}
              onClick={() => setStep("details")}
            >
              Next
            </Button>
          ) : (
            <>
              <Button variant="outline" onClick={() => setStep("photos")}>
                {sale ? "Photos" : "Back"}
              </Button>
              <Button disabled={!canSave} onClick={() => mutation.mutate()}>
                {mutation.isPending && <Loader2 className="animate-spin" />}
                Save
              </Button>
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
