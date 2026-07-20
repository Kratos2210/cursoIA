"use client";

import { useEffect, useRef, useState } from "react";

// Modo escucha con dos capas:
//
//   1. Audio neural pregenerado: un mp3 en /audio/<slug>.mp3 sintetizado con
//      edge-tts (voz es-PE-CamilaNeural). Suena natural, es lo que se reproduce
//      por defecto. Se regenera con:
//        uv run --with edge-tts python web/scripts/generar-audio.py
//   2. Fallback a la Web Speech API del navegador (SpeechSynthesis): gratis y
//      offline, pero robótica. Sólo entra si el mp3 no existe (404 porque aún
//      no se generó) o falla al cargar. Lee título + objetivos + el Recap
//      («en una frase») directamente del DOM.
//
// La caída de la capa 1 a la 2 es transparente: el usuario ve el mismo botón.
export function ListenButton({ title, goals, slug }: { title: string; goals: string | null; slug: string }) {
  const [estado, setEstado] = useState<"idle" | "hablando" | "pausado">("idle");
  const [soportado, setSoportado] = useState(false);
  const utterRef = useRef<SpeechSynthesisUtterance | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  // true = estamos usando el <audio> mp3; false = usamos SpeechSynthesis.
  const usandoAudio = useRef(false);

  useEffect(() => {
    // El botón se muestra si hay AL MENOS una capa disponible: <audio> siempre
    // existe en el navegador; SpeechSynthesis es el respaldo.
    const hayAudio = typeof window !== "undefined" && typeof Audio !== "undefined";
    const haySynth = typeof window !== "undefined" && "speechSynthesis" in window;
    setSoportado(hayAudio || haySynth);
    // Al salir de la página, que no siga sonando por ninguna vía.
    return () => {
      audioRef.current?.pause();
      window.speechSynthesis?.cancel();
    };
  }, []);

  if (!soportado) return null;

  // --- Capa 2: SpeechSynthesis (fallback) -----------------------------------

  const textoSynth = () => {
    const recap = document.querySelector(".recap")?.textContent ?? "";
    const objetivos = (goals ?? "").replace(/^[^A-Za-zÁÉÍÓÚáéíóúñ]*/, "");
    return `${title}. ${objetivos}. En resumen: ${recap}`;
  };

  const hablarSynth = () => {
    const synth = window.speechSynthesis;
    if (!synth) {
      setEstado("idle");
      return;
    }
    synth.cancel();
    const u = new SpeechSynthesisUtterance(textoSynth());
    const voz = synth.getVoices().find((v) => v.lang.startsWith("es"));
    if (voz) u.voice = voz;
    u.lang = voz?.lang ?? "es-PE";
    u.rate = 1.05;
    u.onend = () => setEstado("idle");
    u.onerror = () => setEstado("idle");
    utterRef.current = u; // evita que el GC corte la voz a mitad (bug conocido)
    synth.speak(u);
    setEstado("hablando");
  };

  // --- Capa 1: mp3 neural pregenerado ---------------------------------------

  const reproducirMp3 = () => {
    const audio = new Audio(`/audio/${slug}.mp3`);
    audioRef.current = audio;
    usandoAudio.current = true;
    audio.onended = () => setEstado("idle");
    // Si el mp3 no existe (404) o no carga, caemos a SpeechSynthesis sin ruido.
    audio.onerror = () => {
      usandoAudio.current = false;
      audioRef.current = null;
      hablarSynth();
    };
    audio
      .play()
      .then(() => setEstado("hablando"))
      .catch(() => {
        // play() rechazado (p. ej. mp3 inexistente): fallback transparente.
        usandoAudio.current = false;
        audioRef.current = null;
        hablarSynth();
      });
  };

  // --- Control del botón ----------------------------------------------------

  const alternar = () => {
    // Pausar / seguir sobre la capa activa.
    if (estado === "hablando") {
      if (usandoAudio.current) audioRef.current?.pause();
      else window.speechSynthesis?.pause();
      setEstado("pausado");
      return;
    }
    if (estado === "pausado") {
      if (usandoAudio.current) void audioRef.current?.play();
      else window.speechSynthesis?.resume();
      setEstado("hablando");
      return;
    }
    // Arranque desde cero: siempre se intenta primero el mp3 neural.
    reproducirMp3();
  };

  const parar = () => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
    }
    window.speechSynthesis?.cancel();
    setEstado("idle");
  };

  return (
    <span className="listen">
      <button className="listen-btn" onClick={alternar} aria-live="polite">
        {estado === "hablando" ? "⏸ Pausar" : estado === "pausado" ? "▶ Seguir" : "🔊 Escuchar el resumen"}
      </button>
      {estado !== "idle" ? (
        <button className="listen-btn stop" onClick={parar} aria-label="Detener la lectura">
          ⏹
        </button>
      ) : null}
    </span>
  );
}
