import { Check, Copy } from "lucide-react"
import { useEffect, useState } from "react"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

type Props = {
  value: string
  label: string
  className?: string
}

// Icon button that copies `value` to the clipboard and shows a check mark for a moment.
export function CopyButton({ value, label, className }: Props) {
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    if (!copied) return
    const timer = setTimeout(() => setCopied(false), 1500)
    return () => clearTimeout(timer)
  }, [copied])

  return (
    <Button
      type="button"
      variant="ghost"
      size="icon-xs"
      className={cn("text-muted-foreground", className)}
      aria-label={`Copy ${label}`}
      title={`Copy ${label}`}
      disabled={!value}
      onClick={() =>
        navigator.clipboard.writeText(value).then(
          () => setCopied(true),
          () => toast.error("Couldn't copy to the clipboard"),
        )
      }
    >
      {copied ? <Check className="text-green-600" /> : <Copy />}
    </Button>
  )
}
