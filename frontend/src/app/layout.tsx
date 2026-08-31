import type { Metadata, Viewport } from "next";
import "./globals.css";

import { Providers } from "@/components/auth/providers";
import { ThemeInitScript } from "@/components/theme/theme-init-script";

export const metadata: Metadata = {
  title: "CLOUT",
  description: "Influencer marketing & ads distribution platform",
  icons: {
    icon: [
      { url: "/icon-192.png", sizes: "192x192", type: "image/png" },
      { url: "/icon-512.png", sizes: "512x512", type: "image/png" },
    ],
    apple: "/apple-touch-icon.png",
  },
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: "CLOUT",
  },
};

export const viewport: Viewport = {
  themeColor: "#071827",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className="h-full antialiased"
      suppressHydrationWarning
    >
      <body className="min-h-full flex flex-col">
        <ThemeInitScript />
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
