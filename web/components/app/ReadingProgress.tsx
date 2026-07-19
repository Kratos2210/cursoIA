"use client";

import { useEffect, useState } from "react";

// Thin progress bar pinned to the top of the scroll container (.main), mirroring
// the reading bar from the original single-page course. Tracks .main's scroll,
// not the window's, because .main is the element that actually scrolls.
export function ReadingProgress() {
  const [pct, setPct] = useState(0);

  useEffect(() => {
    const main = document.querySelector<HTMLElement>("[data-main]");
    if (!main) return;
    const update = () => {
      const max = main.scrollHeight - main.clientHeight;
      setPct(max > 0 ? Math.min(100, (main.scrollTop / max) * 100) : 0);
    };
    update();
    main.addEventListener("scroll", update, { passive: true });
    window.addEventListener("resize", update);
    return () => {
      main.removeEventListener("scroll", update);
      window.removeEventListener("resize", update);
    };
  }, []);

  return <div className="read-prog" style={{ width: `${pct}%` }} aria-hidden />;
}
