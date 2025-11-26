import './globals.css'
import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Coperniq Pipeline Dashboard',
  description: 'Pipeline health and observability dashboard for Coperniq contractor lead generation',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className="bg-gray-50 min-h-screen">
        <nav className="bg-coperniq-blue text-white shadow-lg">
          <div className="max-w-7xl mx-auto px-4 py-4">
            <div className="flex items-center justify-between">
              <h1 className="text-xl font-bold">⚡ Coperniq Pipeline</h1>
              <span className="text-sm opacity-75">Observability Dashboard</span>
            </div>
          </div>
        </nav>
        <main className="max-w-7xl mx-auto px-4 py-8">
          {children}
        </main>
        <footer className="text-center text-gray-500 text-sm py-8">
          Data refreshed nightly • Contact engineering for questions
        </footer>
      </body>
    </html>
  )
}
