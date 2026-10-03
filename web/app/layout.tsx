import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = {
  title: "RoleFit — Find your next fit",
  description: "Find AI and data roles backed by the evidence in your CV.",
};
export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
