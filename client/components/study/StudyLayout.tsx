"use client";
import { BookOpenTextIcon, type LucideIcon } from "lucide-react";
import { useState, type ReactNode } from "react";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useIsCompact } from "@/hooks/use-mobile";
import { cn } from "@/lib/utils";

export interface StudyView {
  value: string;
  label: string;
  icon: LucideIcon;
  content: ReactNode;
  /** The view manages its own scrolling (chat keeps its input pinned) */
  fill?: boolean;
  badge?: number;
}

interface Props {
  /** The reading pane: section or collection header plus the study guide */
  guide: ReactNode;
  views: StudyView[];
  guideLabel?: string;
}

/**
 * Study screen. Desktop: the guide on the left, tabbed tools on the right.
 * Phones: one full-height view at a time, picked from a bottom bar (Guide plus
 * each tool), so chat and games get the whole screen instead of a pane below
 * a long narrative. Both panes stay mounted, so switching keeps the reading
 * position, a streaming chat reply and a running game.
 */
export default function StudyLayout({ guide, views, guideLabel = "Guide" }: Props) {
  const isMobile = useIsCompact();
  const [tab, setTab] = useState(views[0].value);
  const [showGuide, setShowGuide] = useState(true);
  const active = views.find((v) => v.value === tab) ?? views[0];
  const guideHidden = isMobile && !showGuide;
  const toolsHidden = isMobile && showGuide;

  const pick = (value: string) => {
    setTab(value);
    setShowGuide(false);
  };

  return (
    <>
      <div className="relative h-[calc(100dvh-3.5rem-var(--bottom-bar))] lg:flex lg:h-[calc(100svh-3.5rem)]">
        <div
          inert={guideHidden}
          className={cn(
            "min-w-0 overflow-y-auto overscroll-contain max-lg:absolute max-lg:inset-0 lg:flex-1",
            guideHidden && "invisible",
          )}
        >
          {guide}
        </div>

        <aside
          inert={toolsHidden}
          className={cn(
            "flex min-h-0 flex-col bg-card/50 max-lg:absolute max-lg:inset-0 lg:w-[460px] lg:shrink-0 lg:border-l xl:w-[520px]",
            toolsHidden && "invisible",
          )}
        >
          <Tabs value={active.value} onValueChange={setTab} className="border-b p-2 max-lg:hidden">
            <TabsList className="w-full">
              {views.map(({ value, label, icon: Icon, badge }) => (
                <TabsTrigger key={value} value={value} className="gap-1.5">
                  <Icon />
                  {label}
                  {!!badge && <Badge variant="secondary" className="h-5 min-w-5 px-1.5 tabular-nums">{badge}</Badge>}
                </TabsTrigger>
              ))}
            </TabsList>
          </Tabs>
          <div className={cn("min-h-0 flex-1", active.fill ? "flex flex-col overflow-hidden" : "overflow-y-auto overscroll-contain")}>
            {active.content}
          </div>
        </aside>
      </div>

      <nav
        aria-label="Study views"
        className="fixed inset-x-0 bottom-0 z-40 border-t bg-background/90 pb-[env(safe-area-inset-bottom)] backdrop-blur-lg lg:hidden"
      >
        <div className="flex h-16 items-stretch px-1">
          {[{ value: "", label: guideLabel, icon: BookOpenTextIcon, badge: 0 }, ...views].map(({ value, label, icon: Icon, badge }) => {
            const selected = value ? !showGuide && value === active.value : showGuide;
            return (
              <button
                key={value || "guide"}
                type="button"
                aria-pressed={selected}
                onClick={() => (value ? pick(value) : setShowGuide(true))}
                className={cn(
                  "relative flex flex-1 flex-col items-center justify-center gap-1 text-[11px] font-medium text-muted-foreground transition-colors active:scale-95",
                  selected && "text-primary",
                )}
              >
                <span className={cn("flex h-7 w-12 items-center justify-center rounded-full transition-colors", selected && "bg-primary/12")}>
                  <Icon className="size-5" />
                </span>
                {label}
                {!!badge && (
                  <span className="absolute top-1.5 left-1/2 ml-2 min-w-4 rounded-full bg-primary px-1 text-[10px] leading-4 text-primary-foreground tabular-nums">
                    {badge}
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </nav>
    </>
  );
}
