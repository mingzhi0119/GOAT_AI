import { Bot, FileText, Activity, Settings } from 'lucide-react';
import { Button } from '@/components/ui/button';

export function SidebarNav() {
    return (
        <div className="w-64 h-screen bg-simonBlue text-white flex flex-col p-4 shrink-0">
            <div className="flex items-center gap-3 px-2 py-4 mb-4">
                <Bot className="w-8 h-8 text-dandelionYellow" />
                <h1 className="text-xl font-bold tracking-tight">GOAT AI</h1>
            </div>
            <nav className="flex-1 space-y-2">
                <Button variant="ghost" className="w-full justify-start text-white hover:text-simonBlue hover:bg-dandelionYellow">
                    <Bot className="mr-3 h-5 w-5" />
                    AI Strategy Chat
                </Button>
                <Button variant="ghost" className="w-full justify-start text-white hover:text-simonBlue hover:bg-dandelionYellow">
                    <FileText className="mr-3 h-5 w-5" />
                    Data Engine
                </Button>
                <Button variant="ghost" className="w-full justify-start text-white hover:text-simonBlue hover:bg-dandelionYellow">
                    <Activity className="mr-3 h-5 w-5" />
                    GPU Telemetry
                </Button>
            </nav>
            <div className="mt-auto">
                <Button variant="ghost" className="w-full justify-start text-white hover:text-simonBlue hover:bg-dandelionYellow">
                    <Settings className="mr-3 h-5 w-5" />
                    Settings
                </Button>
            </div>
        </div>
    );
}
