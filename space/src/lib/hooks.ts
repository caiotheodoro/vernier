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
