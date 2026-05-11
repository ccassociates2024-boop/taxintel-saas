import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cn } from "@/lib/utils";

export function Button({
  className,
  variant = "default",
  asChild = false,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "default" | "outline" | "ghost"; asChild?: boolean }) {
  const Comp = asChild ? Slot : "button";
  return (
    <Comp
      className={cn(
        "inline-flex h-10 items-center justify-center rounded-md px-4 text-sm font-semibold transition disabled:pointer-events-none disabled:opacity-50",
        variant === "default" && "bg-primary text-white hover:opacity-90",
        variant === "outline" && "border bg-card hover:bg-muted/10",
        variant === "ghost" && "hover:bg-muted/10",
        className
      )}
      {...props}
    />
  );
}

