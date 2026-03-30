import { useState } from 'react';
import Markdown from 'react-markdown';
import { Send } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Card } from '@/components/ui/card';

const mockMessages = [
    { role: 'assistant', content: '# Welcome to GOAT AI \n\nI am your strategic intelligence assistant powered by a local A100 GPU. How can I assist you with your business analytics today?\n\n*   Upload data to the **Business Data Engine**\n*   Monitor inference on the **GPU Telemetry** tab.' }
];

export function ChatPanel() {
    const [input, setInput] = useState('');
    const [messages, setMessages] = useState(mockMessages);

    const handleSend = () => {
        if (!input.trim()) return;
        setMessages(prev => [...prev, { role: 'user', content: input }]);
        setInput('');
        setTimeout(() => {
            setMessages(prev => [...prev, { role: 'assistant', content: '*Processing strategic insights...*\n\nBased on your query, the local A100 GPU indicates optimal operational capacity.' }]);
        }, 1000);
    };

    return (
        <div className="flex-1 flex flex-col h-screen bg-gray-50/50">
            <div className="h-14 border-b bg-white flex items-center px-6 shrink-0">
                <h2 className="text-lg font-semibold text-simonBlue">Strategic Intelligence Chat</h2>
            </div>

            <ScrollArea className="flex-1 p-6">
                <div className="max-w-4xl mx-auto space-y-6">
                    {messages.map((msg, i) => (
                        <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                            <Card className={`max-w-[80%] p-4 ${msg.role === 'user' ? 'bg-simonBlue text-white' : 'bg-white'}`}>
                                <div className={`prose prose-sm max-w-none ${msg.role === 'user' ? 'prose-invert' : ''}`}>
                                    <Markdown>{msg.content}</Markdown>
                                </div>
                            </Card>
                        </div>
                    ))}
                </div>
            </ScrollArea>

            <div className="p-4 bg-white border-t shrink-0">
                <div className="max-w-4xl mx-auto flex gap-4">
                    <Input
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                        placeholder="Query your strategic data..."
                        className="flex-1 border-simonBlue/20 focus-visible:ring-simonBlue"
                    />
                    <Button onClick={handleSend} className="bg-dandelionYellow text-simonBlue hover:bg-simonBlue hover:text-white transition-colors">
                        <Send className="h-4 w-4 mr-2" />
                        Analyze
                    </Button>
                </div>
            </div>
        </div>
    );
}
