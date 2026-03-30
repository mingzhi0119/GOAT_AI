import { Bot, FileText, Activity, Settings } from 'lucide-react';
import { Button } from '@/components/ui/button';

const SIMON_LOGO = `${import.meta.env.BASE_URL}urochester_simon_business_horizontal.svg`;

export function SidebarNav() {
    return (
        <div className="w-64 h-screen bg-simonBlue text-white flex flex-col p-4 shrink-0">
            <div className="px-2 pt-2 pb-4 mb-2 border-b border-white/15">
                <div className="rounded-md bg-white px-2 py-2 shadow-sm">
                    <img
                        src={SIMON_LOGO}
                        alt="University of Rochester Simon Business School"
                        className="w-full h-auto max-h-[48px] object-contain object-left"
                        width={220}
                        height={48}
                    />
                </div>
                <p className="mt-3 text-dandelionYellow font-bold text-sm tracking-tight">GOAT AI</p>
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
