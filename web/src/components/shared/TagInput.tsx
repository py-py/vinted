import { Plus, X } from "lucide-react"
import { useId, useRef, useState } from "react"

import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"

type Props = {
  value: string[]
  onChange: (tags: string[]) => void
  // Existing tags offered while typing.
  suggestions?: string[]
  id?: string
  placeholder?: string
  className?: string
}

const normalize = (tag: string) => tag.split(/\s+/).filter(Boolean).join(" ")
const same = (a: string, b: string) => a.toLocaleLowerCase() === b.toLocaleLowerCase()

/**
 * Multi-select of free-form tags, like Jira labels: pick an existing tag or type a new one.
 * Enter / Tab / comma adds the highlighted option, Backspace on an empty field removes the last
 * tag, arrows move through the options, Escape closes them.
 */
export function TagInput({ value, onChange, suggestions = [], id, placeholder, className }: Props) {
  const listId = useId()
  const input = useRef<HTMLInputElement>(null)
  const [text, setText] = useState("")
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState(0)

  const query = normalize(text)
  const matches = suggestions.filter(
    (s) =>
      !value.some((v) => same(v, s)) && s.toLocaleLowerCase().includes(query.toLocaleLowerCase()),
  )
  const canCreate = query !== "" && ![...value, ...suggestions].some((t) => same(t, query))
  // The "create" option goes first so Enter on a new word creates it.
  const options = [
    ...(canCreate ? [{ tag: query, create: true }] : []),
    ...matches.map((tag) => ({ tag, create: false })),
  ]
  const highlighted = options[Math.min(active, options.length - 1)]

  function add(tag: string) {
    const clean = normalize(tag)
    if (clean && !value.some((v) => same(v, clean))) onChange([...value, clean])
    setText("")
    setActive(0)
  }

  function remove(tag: string) {
    onChange(value.filter((v) => v !== tag))
    input.current?.focus()
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter" || e.key === "," || (e.key === "Tab" && query)) {
      if (!highlighted && !query) return
      e.preventDefault()
      // Typed text that is already selected just clears the field.
      add(open && highlighted ? highlighted.tag : query)
    } else if (e.key === "Backspace" && text === "" && value.length > 0) {
      onChange(value.slice(0, -1))
    } else if (e.key === "ArrowDown") {
      e.preventDefault()
      setOpen(true)
      setActive((i) => (options.length ? (i + 1) % options.length : 0))
    } else if (e.key === "ArrowUp") {
      e.preventDefault()
      setActive((i) => (options.length ? (i - 1 + options.length) % options.length : 0))
    } else if (e.key === "Escape" && open) {
      e.preventDefault()
      setOpen(false)
    }
  }

  return (
    <div className={cn("relative", className)}>
      <div
        className="flex min-h-8 w-full cursor-text flex-wrap items-center gap-1 rounded-lg border border-input bg-transparent px-1.5 py-1 transition-colors focus-within:border-ring focus-within:ring-3 focus-within:ring-ring/50 dark:bg-input/30"
        onClick={() => input.current?.focus()}
      >
        {value.map((tag) => (
          <Badge key={tag} variant="secondary" className="max-w-full gap-0.5 pr-0.5">
            <span className="truncate">{tag}</span>
            <button
              type="button"
              className="rounded-full p-0.5 text-muted-foreground hover:bg-muted-foreground/20 hover:text-foreground"
              aria-label={`Remove tag ${tag}`}
              onClick={(e) => {
                e.stopPropagation()
                remove(tag)
              }}
            >
              <X />
            </button>
          </Badge>
        ))}
        <input
          ref={input}
          id={id}
          role="combobox"
          aria-expanded={open && options.length > 0}
          aria-controls={listId}
          aria-autocomplete="list"
          value={text}
          onChange={(e) => {
            // A pasted "a, b, c" adds every complete tag; the part after the last comma stays.
            const parts = e.target.value.split(",")
            if (parts.length > 1) {
              const added = parts.slice(0, -1).map(normalize).filter(Boolean)
              const next = [...value]
              for (const tag of added) if (!next.some((v) => same(v, tag))) next.push(tag)
              if (next.length !== value.length) onChange(next)
            }
            setText(parts.at(-1)!)
            setActive(0)
            setOpen(true)
          }}
          onKeyDown={onKeyDown}
          onFocus={() => setOpen(true)}
          onBlur={() => {
            setOpen(false)
            // Leaving the field keeps what was typed, like Enter.
            if (query) add(query)
          }}
          placeholder={value.length === 0 ? placeholder : undefined}
          className="h-6 min-w-24 flex-1 bg-transparent px-1 text-base outline-none placeholder:text-muted-foreground md:text-sm"
        />
      </div>
      {open && options.length > 0 && (
        <ul
          id={listId}
          role="listbox"
          className="absolute z-50 mt-1 max-h-60 w-full overflow-y-auto rounded-lg border bg-popover p-1 text-sm text-popover-foreground shadow-md"
        >
          {options.map((option) => (
            <li
              key={`${option.create}-${option.tag}`}
              role="option"
              aria-selected={option === highlighted}
              className={cn(
                "flex cursor-pointer items-center gap-2 rounded-md px-2 py-1.5",
                option === highlighted && "bg-accent text-accent-foreground",
              )}
              onMouseEnter={() => setActive(options.indexOf(option))}
              // mousedown, not click: keeps focus in the input so the list stays open.
              onMouseDown={(e) => {
                e.preventDefault()
                add(option.tag)
              }}
            >
              {option.create ? (
                <>
                  <Plus className="size-3.5 text-muted-foreground" />
                  <span>
                    Create <span className="font-medium">"{option.tag}"</span>
                  </span>
                </>
              ) : (
                option.tag
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
