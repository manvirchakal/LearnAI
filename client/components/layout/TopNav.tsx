"use client";
import {
  BookOpenIcon,
  FolderKanbanIcon,
  GraduationCapIcon,
  MenuIcon,
  PanelLeftIcon,
  PlayCircleIcon,
  UploadIcon,
  UserRoundIcon,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useIsMobile } from "@/hooks/use-mobile";
import { cn } from "@/lib/utils";
import { useUIStore } from "@/store/uiStore";
import ThemeToggle from "./ThemeToggle";

const NAV = [
  { href: "/upload", label: "Upload", icon: UploadIcon },
  { href: "/library", label: "Library", icon: BookOpenIcon },
  { href: "/collections", label: "Collections", icon: FolderKanbanIcon },
  { href: "/media", label: "Media", icon: PlayCircleIcon },
  { href: "/questionnaire", label: "Profile", icon: UserRoundIcon },
];

export default function TopNav({ showMenuButton = false }: { showMenuButton?: boolean }) {
  const { toggleSidebar, setTocSheetOpen } = useUIStore();
  const isMobile = useIsMobile();
  const pathname = usePathname();
  const isActive = (href: string) => pathname === href || pathname.startsWith(`${href}/`);

  return (
    <header className="sticky top-0 z-40 h-14 border-b bg-background/80 backdrop-blur-lg supports-[backdrop-filter]:bg-background/60">
      <div className="flex h-full items-center gap-2 px-3 sm:px-4">
        {showMenuButton && (
          <Button variant="ghost" size="icon" onClick={() => (isMobile ? setTocSheetOpen(true) : toggleSidebar())} aria-label="Toggle contents">
            <PanelLeftIcon />
          </Button>
        )}
        <Link href="/home" className="mr-2 flex items-center gap-2 rounded-md px-1 font-semibold tracking-tight">
          <span className="flex size-7 items-center justify-center rounded-lg bg-gradient-to-br from-primary to-chart-2 text-primary-foreground shadow-sm">
            <GraduationCapIcon className="size-4" />
          </span>
          <span className="text-[15px]">LearnAI</span>
        </Link>

        <nav className="ml-auto hidden items-center gap-1 md:flex">
          {NAV.map(({ href, label, icon: Icon }) => (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground",
                isActive(href) && "bg-accent text-accent-foreground",
              )}
            >
              <Icon className="size-4" />
              {label}
            </Link>
          ))}
        </nav>

        <div className="ml-auto flex items-center gap-1 md:ml-2">
          <ThemeToggle />
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="md:hidden" aria-label="Menu">
                <MenuIcon />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-48">
              {NAV.map(({ href, label, icon: Icon }) => (
                <DropdownMenuItem key={href} asChild className={cn(isActive(href) && "bg-accent")}>
                  <Link href={href}>
                    <Icon />
                    {label}
                  </Link>
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
    </header>
  );
}
