import { SidebarNav } from '@/components/layout/SidebarNav';
import { ChatPanel } from '@/components/chat/ChatPanel';

function App() {
  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <SidebarNav />
      <main className="flex-1 flex overflow-hidden">
        <ChatPanel />
      </main>
    </div>
  )
}

export default App;
