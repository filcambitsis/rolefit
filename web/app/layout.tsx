import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = {
  title: "RoleFit — Find your next fit",
  description:
    "Find AI, data and software jobs in the Netherlands, with requirement coverage linked to your CV.",
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
