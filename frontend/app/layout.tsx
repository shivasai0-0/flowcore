import type { Metadata } from 'next';
import './globals.css';
import { WorkspaceProvider } from '@/context/workspace-context';

export const metadata: Metadata = {
  title: 'FlowCore — AI-Powered WhatsApp Business Automation',
  description: 'Deploy deterministic conversational workflow automation instantly via natural language commands powered by local Llama.',
  keywords: 'whatsapp, chatbot, automation, fsm, deterministic, artificial intelligence, nextjs, reactflow',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full scroll-smooth" suppressHydrationWarning>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Outfit:wght@400;500;600;700;800&display=swap" rel="stylesheet" />
      </head>
      <body className="min-h-full flex flex-col antialiased selection:bg-emerald-500/30 selection:text-white">
        <WorkspaceProvider>
          {children}
        </WorkspaceProvider>
      </body>
    </html>
  );
}
