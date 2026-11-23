import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SemantiQL — Ask your data",
  description: "Translate business language into explainable PostgreSQL queries.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
