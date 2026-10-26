import "cropperjs/dist/cropper.css"

import Cropper from "cropperjs"
import { Crop, RotateCw } from "lucide-react"
import { useCallback, useRef, useState } from "react"

import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { cn } from "@/lib/utils"

// The backend re-encodes and downsizes to 1200 px anyway; keep the upload lossless-ish.
const JPEG_QUALITY = 0.92

type Props = {
  src: string
  onSave: (file: Blob) => void
  onClose: () => void
}

// Vinted-style "Edit photo" dialog: rotate by 90° and an optional crop box.
// Done hands the edited JPEG back; saving it is up to the caller.
export function PhotoEditor({ src, onSave, onClose }: Props) {
  const cropperRef = useRef<Cropper | null>(null)
  const [ready, setReady] = useState(false)
  const [cropping, setCropping] = useState(false)
  const [rotated, setRotated] = useState(false)

  // Callback ref, not an effect: the dialog content (and so the <img>) mounts after this
  // component's effects run.
  const imageRef = useCallback((image: HTMLImageElement | null) => {
    if (!image) return
    const cropper = new Cropper(image, {
      viewMode: 1,
      autoCrop: false,
      dragMode: "none",
      background: false,
      zoomable: false,
      toggleDragModeOnDblclick: false,
      // Listing photos are served same-origin; no CORS round-trip needed.
      checkCrossOrigin: false,
      ready: () => setReady(true),
    })
    cropperRef.current = cropper
    return () => {
      cropper.destroy()
    }
  }, [])

  function rotate() {
    const cropper = cropperRef.current!
    cropper.clear()
    cropper.rotate(90)
    // A rotated landscape photo overflows the box; scale it back to fit, centered.
    const box = cropper.getContainerData()
    const canvas = cropper.getCanvasData()
    const ratio = Math.min(box.width / canvas.width, box.height / canvas.height)
    const width = canvas.width * ratio
    const height = canvas.height * ratio
    cropper.setCanvasData({
      left: (box.width - width) / 2,
      top: (box.height - height) / 2,
      width,
      height,
    })
    if (cropping) cropper.crop()
    setRotated(true)
  }

  function toggleCrop() {
    const cropper = cropperRef.current!
    if (cropping) {
      cropper.clear()
      cropper.setDragMode("none")
    } else {
      cropper.crop()
      cropper.setDragMode("crop")
    }
    setCropping(!cropping)
  }

  function save() {
    cropperRef.current!
      .getCroppedCanvas({ imageSmoothingQuality: "high" })
      .toBlob((blob) => blob && onSave(blob), "image/jpeg", JPEG_QUALITY)
  }

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="gap-0 p-0 sm:max-w-md">
        <DialogHeader className="border-b p-4">
          <DialogTitle className="text-center">Edit photo</DialogTitle>
          <DialogDescription className="sr-only">Rotate or crop the photo</DialogDescription>
        </DialogHeader>
        <div className="flex justify-center gap-6 pt-4">
          <Button variant="ghost" onClick={rotate} disabled={!ready}>
            <RotateCw />
            Rotate
          </Button>
          <Button
            variant="ghost"
            onClick={toggleCrop}
            disabled={!ready}
            aria-pressed={cropping}
            className={cn(cropping && "bg-muted")}
          >
            <Crop />
            Crop
          </Button>
        </div>
        <div className="p-4">
          {/* Cropper sizes itself to the image's parent: a padding-free box of fixed height. */}
          <div className="h-[min(60vh,28rem)]">
            <img ref={imageRef} src={src} alt="" className="block max-w-full" />
          </div>
        </div>
        {/* Not DialogFooter: its negative margins assume the default content padding. */}
        <div className="grid grid-cols-2 gap-3 p-4 pt-0">
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={save} disabled={!ready || !(rotated || cropping)}>
            Done
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
