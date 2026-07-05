import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "oss-scout · agent 项目审阅",
  description: "发现 AI agent 领域开源项目，审阅优化提案，确认后回本地执行",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh">
      <body>{children}</body>
    </html>
  );
}
