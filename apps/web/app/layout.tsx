import "./globals.css";
import type { ReactNode } from "react";

export const metadata = {
  title: "Veridex",
  description: "AI-powered evidence investigation",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <header className="border-b bg-white px-6 py-4">
          <a href="/" className="text-lg font-semibold">
            Veridex
          </a>
          <p className="text-sm text-stone-600">Reconstruct the truth from evidence.</p>
        </header>
        <main className="mx-auto max-w-5xl px-6 py-6">{children}</main>
      </body>
    </html>
  );
}
