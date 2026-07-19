"use client";

import { useEffect, useRef, useState } from "react";

// Modo escucha con la Web Speech API del navegador: gratis, offline y sin
// hosting de audio. La voz es la del sistema (robótica, sí) — el objetivo es
// accesibilidad y repaso con las manos ocupadas, no producción de podcast.
// Lee: título + objetivos + el Recap («en una frase») del propio DOM.
export function ListenButton({ title, goals }: { title: string; goals: string | null }) {
  const [estado, setEstado] = useState<"idle" | "hablando" | "pausado">("idle");
  const [soportado, setSoportado] = useState(false);
  const utterRef = useRef<SpeechSynthesisUtterance | null>(null);

  useEffect(() => {
    setSoportado(typeof window !== "undefined" && "speechSynthesis" in window);
    // Al salir de la página, que no siga hablando.
    return () => window.speechSynthesis?.cancel();
  }, []);

  if (!soportado) return null;

  const texto = () => {
    const recap = document.querySelector(".recap")?.textContent ?? "";
    const objetivos = (goals ?? "").replace(/^[^A-Za-zÁÉÍÓÚáéíóúñ]*/, "");
    return `${title}. ${objetivos}. En resumen: ${recap}`;
  };

  const hablar = () => {
    const synth = window.speechSynthesis;
    if (estado === "hablando") {
      synth.pause();
      setEstado("pausado");
      return;
    }
    if (estado === "pausado") {
      synth.resume();
      setEstado("hablando");
      return;
    }
    synth.cancel();
    const u = new SpeechSynthesisUtterance(texto());
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

  const parar = () => {
    window.speechSynthesis.cancel();
    setEstado("idle");
  };

  return (
    <span className="listen">
      <button className="listen-btn" onClick={hablar} aria-live="polite">
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
