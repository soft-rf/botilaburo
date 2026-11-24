import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Agarra la pala - Ofertas de Empleo en Tiempo Real",
  description: "Monitoreo y filtrado inteligente de ofertas de empleo recién publicadas",
  manifest: "/manifest.json",
  icons: {
    icon: "/logo.svg",
    shortcut: "/logo.svg",
    apple: "/logo.svg",
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
  themeColor: "#0D3878",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="es">
      <body className="min-h-screen bg-[#F3F5F8] text-[#1F2937] antialiased selection:bg-[#F36F21] selection:text-white">
        {children}
      </body>
    </html>
  );
}
