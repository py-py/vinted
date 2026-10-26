import {
  closestCenter,
  DndContext,
  KeyboardSensor,
  PointerSensor,
  TouchSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core"
import {
  arrayMove,
  rectSortingStrategy,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
} from "@dnd-kit/sortable"
import { CSS } from "@dnd-kit/utilities"
import { Camera, Pencil, X } from "lucide-react"
import { useState } from "react"

import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import type { ListingPhoto } from "@/lib/api"
import { cn } from "@/lib/utils"

type Props = {
  photos: ListingPhoto[]
  // Uploads in flight, shown as placeholder tiles after the photos.
  pending?: number
  onReorder: (photos: ListingPhoto[]) => void
  onOpen: (index: number) => void
  onEdit: (photo: ListingPhoto) => void
  onRemove: (photo: ListingPhoto) => void
  onAdd: () => void
  // Image files dropped onto the add tile.
  onDropFiles: (files: File[]) => void
}

// Vinted-like photo grid: drag to reorder, the first photo is the main one.
export function ListingPhotoGrid({
  photos,
  pending = 0,
  onReorder,
  onOpen,
  onEdit,
  onRemove,
  onAdd,
  onDropFiles,
}: Props) {
  const [dragOver, setDragOver] = useState(false)
  const sensors = useSensors(
    // A small distance / delay keeps clicks on a photo and touch scrolling working.
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
    useSensor(TouchSensor, { activationConstraint: { delay: 200, tolerance: 6 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  )

  function onDragEnd({ active, over }: DragEndEvent) {
    if (!over || active.id === over.id) return
    const from = photos.findIndex((p) => p.id === active.id)
    const to = photos.findIndex((p) => p.id === over.id)
    onReorder(arrayMove(photos, from, to))
  }

  return (
    <div className="space-y-3">
      <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={onDragEnd}>
        <SortableContext items={photos.map((p) => p.id)} strategy={rectSortingStrategy}>
          <ol className="grid grid-cols-3 gap-2 sm:grid-cols-5 md:grid-cols-6 lg:grid-cols-8">
            {photos.map((photo, i) => (
              <SortablePhoto
                key={photo.id}
                photo={photo}
                index={i}
                onOpen={() => onOpen(i)}
                onEdit={() => onEdit(photo)}
                onRemove={() => onRemove(photo)}
              />
            ))}
            {Array.from({ length: pending }, (_, i) => (
              <li key={`pending-${i}`} className="aspect-square">
                <Skeleton className="size-full rounded-lg" />
              </li>
            ))}
            <li className="aspect-square">
              <button
                type="button"
                onClick={onAdd}
                onDragOver={(e) => {
                  e.preventDefault()
                  setDragOver(true)
                }}
                onDragLeave={() => setDragOver(false)}
                onDrop={(e) => {
                  e.preventDefault()
                  setDragOver(false)
                  onDropFiles([...e.dataTransfer.files])
                }}
                aria-label="Add photos"
                className={cn(
                  "flex size-full items-center justify-center rounded-lg border-2 border-dashed text-muted-foreground hover:bg-muted",
                  dragOver && "border-primary bg-muted",
                )}
              >
                <Camera className="size-6" />
              </button>
            </li>
          </ol>
        </SortableContext>
      </DndContext>
      {photos.length > 1 && (
        <p className="text-center text-sm text-muted-foreground">
          Click and drag to change the order of your photos.
        </p>
      )}
    </div>
  )
}

type SortablePhotoProps = {
  photo: ListingPhoto
  index: number
  onOpen: () => void
  onEdit: () => void
  onRemove: () => void
}

function SortablePhoto({ photo, index, onOpen, onEdit, onRemove }: SortablePhotoProps) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: photo.id,
  })

  return (
    <li
      ref={setNodeRef}
      style={{ transform: CSS.Transform.toString(transform), transition }}
      className={cn("relative aspect-square touch-manipulation", isDragging && "z-10 opacity-80")}
    >
      <button
        type="button"
        {...attributes}
        {...listeners}
        onClick={onOpen}
        aria-label={`Photo ${index + 1}${index === 0 ? " (main)" : ""}: open, or drag to reorder`}
        className={cn(
          "size-full cursor-grab overflow-hidden rounded-lg bg-muted active:cursor-grabbing",
          isDragging && "shadow-lg",
        )}
      >
        <img
          src={photo.url}
          alt=""
          loading="lazy"
          draggable={false}
          className="size-full object-cover"
        />
      </button>
      <Button
        size="icon-sm"
        variant="outline"
        className="absolute top-2 right-2 bg-background"
        aria-label={`Delete photo ${index + 1}`}
        onClick={onRemove}
      >
        <X />
      </Button>
      <Button
        size="icon-sm"
        variant="outline"
        className="absolute right-2 bottom-2 bg-background"
        aria-label={`Edit photo ${index + 1}`}
        onClick={onEdit}
      >
        <Pencil />
      </Button>
      {index === 0 && (
        <span className="pointer-events-none absolute bottom-2 left-2 rounded-full bg-background px-2.5 py-0.5 text-xs text-muted-foreground">
          Main
        </span>
      )}
    </li>
  )
}
