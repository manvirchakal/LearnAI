"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { MOBILE_NAV, isActivePath } from "./nav";

/** Phone tab bar: the app's sections within thumb reach (hidden from md up, where TopNav lists them) */
export default function MobileNav() {
  const pathname = usePathname();
  return (
    <nav
      aria-label="Main"
      className="fixed inset-x-0 bottom-0 z-40 border-t bg-background/90 pb-[env(safe-area-inset-bottom)] backdrop-blur-lg md:hidden"
    >
      <div className="flex h-16 items-stretch px-1">
        {MOBILE_NAV.map(({ href, label, icon: Icon }) => {
          const active = isActivePath(pathname, href);
          return (
            <Link
              key={href}
              href={href}
              aria-current={active ? "page" : undefined}
              className={cn(
                "flex flex-1 flex-col items-center justify-center gap-1 text-[11px] font-medium text-muted-foreground transition-colors active:scale-95",
                active && "text-primary",
              )}
            >
              <span className={cn("flex h-7 w-12 items-center justify-center rounded-full transition-colors", active && "bg-primary/12")}>
                <Icon className="size-5" />
              </span>
              {label}
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
