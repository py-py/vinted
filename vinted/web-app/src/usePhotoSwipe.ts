import { useEffect } from 'react'
import PhotoSwipeLightbox from 'photoswipe/lightbox'
import 'photoswipe/style.css'

// Minimal shapes for the internals we mutate when refitting a slide.
interface SlideLike {
  width: number
  height: number
  zoomLevels?: { initial: number }
  calculateSize?: () => void
  setZoomLevel?: (z: number) => void
  applyCurrentZoomPan?: () => void
}
interface ContentLike {
  width?: number
  height?: number
}

// One lightbox bound to every `.pswp-gallery` on the page. Re-initialised when
// `dep` changes (e.g. the filtered set of cards), since PhotoSwipe wires up
// click handlers per gallery element at init time.
export function usePhotoSwipe(dep: unknown): void {
  useEffect(() => {
    const lightbox = new PhotoSwipeLightbox({
      gallery: '.pswp-gallery',
      // Only photo anchors (they carry data-pswp-width); leaves other links in
      // the gallery — e.g. the "Open on Vinted" icon — to navigate normally.
      children: 'a[data-pswp-width]',
      pswpModule: () => import('photoswipe'),
    })

    // Cards seed real dimensions lazily; refit the slide if it opened with the
    // placeholder size before the natural size was known.
    lightbox.on('loadComplete', (e) => {
      const el = e.content.element
      if (!(el instanceof HTMLImageElement)) return
      const w = el.naturalWidth
      const h = el.naturalHeight
      const slide = e.slide as unknown as SlideLike
      const content = e.content as unknown as ContentLike
      if (!w || (slide.width === w && slide.height === h)) return
      content.width = slide.width = w
      content.height = slide.height = h
      slide.calculateSize?.()
      slide.setZoomLevel?.(slide.zoomLevels?.initial ?? 1)
      slide.applyCurrentZoomPan?.()
    })

    lightbox.init()
    return () => lightbox.destroy()
  }, [dep])
}
