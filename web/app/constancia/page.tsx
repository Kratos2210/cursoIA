import type { Metadata } from "next";
import { Constancia } from "@/components/app/Constancia";

export const metadata: Metadata = {
  title: "Constancia · AI Engineer",
  description:
    "Tu constancia de finalización del curso: se desbloquea al completar el 100% de los conceptos y recursos.",
};

export default function ConstanciaPage() {
  return <Constancia />;
}
