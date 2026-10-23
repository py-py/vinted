// Vinted shows photos at up to 1600px; anything larger only slows the upload.
export const MAX_PHOTO_SIDE = 1600
const JPEG_QUALITY = 0.85

/** Scale an image so its longest side is at most `maxSide` and re-encode it as JPEG. */
export async function resizeImage(file: File, maxSide = MAX_PHOTO_SIDE): Promise<Blob> {
  // "from-image" applies EXIF rotation, so phone photos keep their orientation.
  const bitmap = await createImageBitmap(file, { imageOrientation: "from-image" })
  const scale = Math.min(1, maxSide / Math.max(bitmap.width, bitmap.height))
  const canvas = document.createElement("canvas")
  canvas.width = Math.round(bitmap.width * scale)
  canvas.height = Math.round(bitmap.height * scale)

  const ctx = canvas.getContext("2d")!
  ctx.imageSmoothingQuality = "high"
  ctx.drawImage(bitmap, 0, 0, canvas.width, canvas.height)
  bitmap.close()

  return new Promise((resolve, reject) =>
    canvas.toBlob(
      (blob) => (blob ? resolve(blob) : reject(new Error("Failed to encode JPEG"))),
      "image/jpeg",
      JPEG_QUALITY,
    ),
  )
}
