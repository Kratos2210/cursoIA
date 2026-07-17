import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Curso: LangChain, RAG y LangGraph desde cero",
  description:
    "Curso práctico de LangChain, RAG y LangGraph — de tu primer modelo a un AI Engineer, con ejemplos ejecutables y autoevaluaciones.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="es-PE">
      <body>{children}</body>
    </html>
  );
}
