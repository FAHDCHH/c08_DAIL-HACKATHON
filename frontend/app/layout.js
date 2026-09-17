import "./globals.css";

export const metadata = {
  title: "Evidence Console — Schmitz-Stiftungen",
  description: "Evidence-based program reporting (exercise demo)",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
