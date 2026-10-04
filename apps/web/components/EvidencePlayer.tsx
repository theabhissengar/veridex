"use client";

import { useEffect, useRef } from "react";

type Box = { x: number; y: number; w: number; h: number };

export function EvidencePlayer({ src, timestampMs, bbox }: { src: string; timestampMs: number | null; bbox: Box | null }) {
  const video = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    const element = video.current;
    if (!element || timestampMs == null) return;
    const seek = () => {
      element.currentTime = timestampMs / 1000;
    };
    if (element.readyState >= 1) seek();
    else element.addEventListener("loadedmetadata", seek, { once: true });
  }, [src, timestampMs]);

  return (
    <div className="relative bg-black">
      <video ref={video} src={src} controls className="max-h-80 w-full" data-timestamp-ms={timestampMs ?? ""} />
      {bbox ? (
        <div
          data-testid="detection-box"
          className="pointer-events-none absolute border-2 border-amber-400"
          style={{ left: `${bbox.x * 100}%`, top: `${bbox.y * 100}%`, width: `${bbox.w * 100}%`, height: `${bbox.h * 100}%` }}
        />
      ) : null}
    </div>
  );
}
