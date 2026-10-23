import { useSearchParams } from "react-router"

/**
 * Page state kept in the URL query so reloads and shared links keep it.
 * `update` replaces the given keys (arrays become repeated params, empty values are
 * dropped) and resets `page` unless the patch sets it.
 */
export function useUrlParams() {
  const [params, setParams] = useSearchParams()

  const update = (patch: Record<string, string | string[]>) => {
    const next = new URLSearchParams(params)
    for (const [key, value] of Object.entries(patch)) {
      next.delete(key)
      ;[value].flat().filter(Boolean).forEach((v) => next.append(key, v))
    }
    if (!("page" in patch)) next.delete("page")
    setParams(next, { replace: true })
  }

  return [params, update] as const
}
