import { Inter, Playfair_Display } from "next/font/google";
import type { Metadata } from "next";
import { UIProvider } from "@/context/UIContext";
import "./globals.css";

const recoleta = Playfair_Display({
  subsets: ["latin"],
  weight: ["400"],
  variable: "--font-recoleta",
  display: "swap",
});

const grotesk = Inter({
  subsets: ["latin"],
  weight: ["300", "400", "500"],
  variable: "--font-grotesk",
  display: "swap",
});

export const metadata: Metadata = {
  title: "DocIntel — Document Intelligence",
  description:
    "Domain-aware technical document intelligence. Upload, index, and query with grounded RAG.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="bg-midnight">
      <body className={`${recoleta.variable} ${grotesk.variable}`}>
        <UIProvider>{children}</UIProvider>
      </body>
    </html>
  );
}
