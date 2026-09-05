import { useEffect, useRef, useState, type RefObject } from "react";

/** Measured content-box width of an element, updated by ResizeObserver. */
export function useWidth<T extends HTMLElement>(): [RefObject<T>, number] {
  const ref = useRef<T>(null);
  const [width, setWidth] = useState(0);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const ro = new ResizeObserver((entries) => {
      for (const entry of entries) setWidth(Math.floor(entry.contentRect.width));
    });
    ro.observe(el);
    setWidth(Math.floor(el.getBoundingClientRect().width));
    return () => ro.disconnect();
  }, []);
  return [ref, width];
}

export function prefersReducedMotion(): boolean {
  return typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

/** 0 -> 1 over `ms` with ease-out, restarted whenever `key` changes. Reduced motion: 1 at once. */
export function useEaseIn(key: string, ms: number): number {
  const [t, setT] = useState(prefersReducedMotion() ? 1 : 0);
  useEffect(() => {
    if (prefersReducedMotion()) {
      setT(1);
      return;
    }
    let raf = 0;
    const start = performance.now();
    setT(0);
    const step = (now: number): void => {
      const x = Math.min(1, (now - start) / ms);
      setT(1 - Math.pow(1 - x, 3));
      if (x < 1) raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [key, ms]);
  return t;
}

export function cssToken(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

/**
 * The one motion device: reveal on entry, once. Fires 80px before the element's bottom edge,
 * unobserves immediately, and does nothing at all when `html.motion` is absent (reduced motion,
 * or JS that failed before main.tsx ran) -- in which case the CSS leaves everything visible.
 */
export function useFadeIn(ready: boolean): void {
  useEffect(() => {
    if (!ready || !document.documentElement.classList.contains("motion")) return;
    const targets = [...document.querySelectorAll("[data-fade]")];

    // Anything already on screen is revealed without waiting for a callback. Above-the-fold
    // content should never depend on an observer firing -- and in a hidden or throttled tab the
    // observer may not deliver at all, which would otherwise leave the page blank.
    const reveal = (el: Element): void => el.setAttribute("data-visible", "");
    const onScreen = (el: Element): boolean => el.getBoundingClientRect().top < window.innerHeight;
    for (const el of targets) if (onScreen(el)) reveal(el);

    const rest = targets.filter((el) => !el.hasAttribute("data-visible"));
    if (rest.length === 0) return;
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (!entry.isIntersecting) continue;
          reveal(entry.target);
          observer.unobserve(entry.target);
        }
      },
      { rootMargin: "0px 0px -80px 0px" },
    );
    for (const el of rest) observer.observe(el);
    return () => observer.disconnect();
  }, [ready]);
}

/**
 * The committed sprite atlas, decoded once. Returns null until it lands, and stays null if it
 * cannot be fetched -- in which case every tile falls back to its judge-output card, which is
 * the same thing the 576 unshipped frames show anyway.
 */
export function useAtlas(stats: { thumbnails?: { atlas?: { file?: string } } }): ImageBitmap | null {
  const [bitmap, setBitmap] = useState<ImageBitmap | null>(null);
  const file = stats.thumbnails?.atlas?.file;
  useEffect(() => {
    if (!file) return;
    let live = true;
    const url = `${import.meta.env.BASE_URL}${file}`;
    void fetch(url)
      .then((res) => (res.ok ? res.blob() : Promise.reject(new Error(`atlas HTTP ${res.status}`))))
      .then(createImageBitmap)
      .then((b) => {
        if (live) setBitmap(b);
      })
      .catch(() => setBitmap(null));
    return () => {
      live = false;
    };
  }, [file]);
  return bitmap;
}
