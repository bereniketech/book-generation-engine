import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Book Generation Engine",
  description: "AI-powered book generation",
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
