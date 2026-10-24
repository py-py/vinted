import { ImageOff } from "lucide-react"
import { useState, type ComponentProps } from "react"

import { cn } from "@/lib/utils"

type Props = Omit<ComponentProps<"img">, "src"> & {
  src?: string
  // GCS copy (`stored_photo_urls`), used once the Vinted CDN URL stops loading.
  fallback?: string
}

export function Photo({ src, fallback, className, alt, ...props }: Props) {
  const [failed, setFailed] = useState<string[]>([])
  const current = [src, fallback].find((url) => url && !failed.includes(url))

  // No photo saved (listing deleted before sync) or every URL failed to load.
  if (!current) {
    return (
      <div
        role="img"
        aria-label={alt || "No photo"}
        className={cn("flex items-center justify-center text-muted-foreground", className)}
      >
        <ImageOff className="size-1/3 max-h-8 max-w-8" />
      </div>
    )
  }

  return (
    <img
      {...props}
      className={className}
      alt={alt}
      src={current}
      onError={() => setFailed((f) => [...f, current])}
      referrerPolicy="no-referrer"
    />
  )
}
