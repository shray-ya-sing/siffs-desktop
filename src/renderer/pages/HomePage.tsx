import { useState } from "react"
import { GlassSidebar } from "../components/GlassSidebar"
import { MainContent } from "../components/MainContent"

export function HomePage() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)

  return (
    <div className="relative min-h-screen">
      <div className="fixed inset-0 glass-morphism-frosted -z-10" />

      <GlassSidebar collapsed={sidebarCollapsed} onToggle={() => setSidebarCollapsed(!sidebarCollapsed)} />
      <MainContent sidebarCollapsed={sidebarCollapsed} />
    </div>
  )
}
