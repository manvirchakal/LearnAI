import { useSyncExternalStore } from "react";

/** Live result of a CSS media query. False during server rendering. */
export function useMediaQuery(query: string) {
  return useSyncExternalStore(
    (onChange) => {
      const mql = window.matchMedia(query);
      mql.addEventListener("change", onChange);
      return () => mql.removeEventListener("change", onChange);
    },
    () => window.matchMedia(query).matches,
    () => false,
  );
}

/** True below the md breakpoint (768px) */
export function useIsMobile() {
  return useMediaQuery("(max-width: 767px)");
}

/** True below the lg breakpoint (1024px), where study screens show one pane at a time */
export function useIsCompact() {
  return useMediaQuery("(max-width: 1023px)");
}
