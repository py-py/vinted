import { useState, type ComponentProps } from "react"

type Props = Omit<ComponentProps<"img">, "src"> & {
  src?: string
  // GCS copy (`stored_photo_urls`), used once the Vinted CDN URL stops loading.
  fallback?: string
}

export function Photo({ src, fallback, ...props }: Props) {
  const [failedSrc, setFailedSrc] = useState<string>()
  const current = failedSrc === src && fallback ? fallback : src

  return (
    <img
      {...props}
      src={current}
      onError={() => setFailedSrc(src)}
      referrerPolicy="no-referrer"
    />
  )
}
