"use client";

import { useState } from "react";

// Lite-embed sin dependencias: hasta que el alumno no pulsa play, la página
// solo carga una miniatura estática — cero JS de YouTube, cero cookies. Al
// pulsar, se monta el iframe de youtube-nocookie con autoplay.
function youtubeId(url: string): string | null {
  const m =
    /(?:youtu\.be\/|youtube(?:-nocookie)?\.com\/(?:watch\?v=|embed\/|shorts\/))([\w-]{6,})/.exec(url);
  return m ? m[1] : null;
}

export function VideoEmbed({ url, title }: { url: string; title: string }) {
  const [playing, setPlaying] = useState(false);
  const id = youtubeId(url);
  if (!id) return null;

  return (
    <div className="video-embed">
      {playing ? (
        <iframe
          src={`https://www.youtube-nocookie.com/embed/${id}?autoplay=1`}
          title={`Video: ${title}`}
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
          allowFullScreen
        />
      ) : (
        <button
          className="video-cover"
          onClick={() => setPlaying(true)}
          aria-label={`Reproducir el video de ${title}`}
        >
          {/* eslint-disable-next-line @next/next/no-img-element -- miniatura externa de YouTube; next/image exigiría configurar el dominio remoto */}
          <img src={`https://i.ytimg.com/vi/${id}/hqdefault.jpg`} alt="" loading="lazy" />
          <span className="video-play" aria-hidden>▶</span>
          <span className="video-label">Ver el video de esta ruta</span>
        </button>
      )}
    </div>
  );
}
