import type { Metadata } from "next";
import { Diagnostico } from "@/components/interactive/Diagnostico";

export const metadata: Metadata = {
  title: "¿Por dónde empiezo? · Diagnóstico de nivel",
  description:
    "Diez preguntas para saber en qué ruta del curso entrar y qué conceptos puedes saltarte.",
};

export default function DiagnosticoPage() {
  return <Diagnostico />;
}
