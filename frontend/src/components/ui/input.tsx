import * as React from "react"

import { cn } from "@/lib/utils"

const Input = React.forwardRef<HTMLInputElement, React.ComponentProps<"input">>(
  ({ className, type, ...props }, ref) => {
    return (
      <input
        type={type}
        className={cn(
          "flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-base text-foreground ring-offset-background",
          /* file inputs: style ::file-selector-button so “Browse/Choose file” is readable in light mode */
          "file:mr-3 file:inline-flex file:h-8 file:cursor-pointer file:items-center file:rounded-md file:border-0 file:bg-simonBlue file:px-3 file:text-sm file:font-semibold file:text-white file:shadow-sm hover:file:bg-[#003a72]",
          "placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 md:text-sm",
          type === "file" && "min-h-10 py-1.5",
          className
        )}
        ref={ref}
        {...props}
      />
    )
  }
)
Input.displayName = "Input"

export { Input }
