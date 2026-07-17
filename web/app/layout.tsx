import type { Metadata } from "next";
import { Manrope, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { AppProvider } from "@/components/app/AppProvider";
import { Sidebar } from "@/components/app/Sidebar";
import { MobileBar } from "@/components/app/MobileBar";

const manrope = Manrope({
  variable: "--font-manrope",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700", "800"],
});
const jetbrains = JetBrains_Mono({
  variable: "--font-jetbrains",
  subsets: ["latin"],
  weight: ["400", "500", "600"],
});

export const metadata: Metadata = {
  title: "AI Engineer · Ruta de cero a pro",
  description:
    "Roadmap de cero a AI Engineer: seis niveles, de instalar Python a sistemas de IA en producción, con un proyecto integrador por nivel.",
};

// Sets data-theme before paint from the stored preference (or the OS default),
// avoiding a flash of the wrong theme.
const themeScript = `(function(){try{var s=JSON.parse(localStorage.getItem('curso_ia_v3')||'{}');var t=s.theme||(matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light');document.documentElement.setAttribute('data-theme',t);}catch(e){document.documentElement.setAttribute('data-theme','light');}})();`;

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html
      lang="es-PE"
      className={`${manrope.variable} ${jetbrains.variable}`}
      suppressHydrationWarning
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body>
        <a href="#contenido" className="skip-link">
          Saltar al contenido
        </a>
        <AppProvider>
          <div className="app">
            <Sidebar />
            <main className="main" data-main>
              <MobileBar />
              <div className="main-inner" id="contenido" tabIndex={-1}>
                {children}
              </div>
            </main>
          </div>
        </AppProvider>
      </body>
    </html>
  );
}
