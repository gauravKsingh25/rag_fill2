import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "@/contexts/AuthContext";
import AuthGuard from "@/components/auth/AuthGuard";
import Navigation from "@/components/Navigation";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  display: 'swap',
});

export const metadata: Metadata = {
  title: "RAG System - Multi-Device Knowledge Base",
  description: "Advanced RAG system with device isolation and template processing",
  keywords: ["RAG", "AI", "Document Processing", "Machine Learning", "Knowledge Base"],
  authors: [{ name: "RAG System Team" }],
  viewport: "width=device-width, initial-scale=1",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning={true}>
      <body
        className={`${inter.variable} font-inter antialiased`}
        suppressHydrationWarning={true}
      >
        <AuthProvider>
          <AuthGuard>
            <div className="min-h-screen bg-gradient-to-br from-gray-50 to-white">
              <Navigation />
              <main className="w-full">
                {children}
              </main>
            </div>
          </AuthGuard>
        </AuthProvider>
      </body>
    </html>
  );
}
