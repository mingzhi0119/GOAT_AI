import { useEffect, useState } from "react";
import Markdown from "react-markdown";
import { Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Card } from "@/components/ui/card";
import { fetchOllamaModels, getDefaultModel, streamGenerate } from "@/lib/ollama";

const WELCOME = `# Welcome to GOAT AI

I am your strategic intelligence assistant powered by a local A100 GPU. How can I assist you with your business analytics today?

* Upload data to the **Business Data Engine**
* Monitor inference on the **GPU Telemetry** tab.`;

type Msg = { role: "user" | "assistant"; content: string };

export function ChatPanel() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Msg[]>([{ role: "assistant", content: WELCOME }]);
  const [model, setModel] = useState(getDefaultModel());
  const [models, setModels] = useState<string[]>([getDefaultModel()]);
  const [loading, setLoading] = useState(false);
  const [modelErr, setModelErr] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchOllamaModels()
      .then((list) => {
        if (!cancelled) {
          setModels(list);
          setModel((m) => (list.includes(m) ? m : list[0] ?? m));
        }
      })
      .catch((e: unknown) => {
        if (!cancelled) {
          setModelErr(e instanceof Error ? e.message : "Could not list Ollama models");
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || loading) return;

    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setMessages((prev) => [...prev, { role: "assistant", content: "" }]);
    setLoading(true);

    let full = "";
    try {
      for await (const token of streamGenerate(model, text)) {
        full += token;
        setMessages((prev) => {
          const next = [...prev];
          next[next.length - 1] = { role: "assistant", content: full };
          return next;
        });
      }
      if (!full.trim()) {
        setMessages((prev) => {
          const next = [...prev];
          next[next.length - 1] = {
            role: "assistant",
            content: "_No text returned. Is the model pulled? (`ollama pull " + model + "`)_",
          };
          return next;
        });
      }
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      setMessages((prev) => {
        const next = [...prev];
        next[next.length - 1] = {
          role: "assistant",
          content: `**Could not reach Ollama.** ${msg}\n\nCheck that \`ollama serve\` is running and the dev proxy or \`VITE_OLLAMA_BASE_URL\` is set correctly.`,
        };
        return next;
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex-1 flex flex-col h-screen bg-gray-50/50">
      <div className="h-14 border-b bg-white flex items-center px-6 shrink-0 gap-4">
        <h2 className="text-lg font-semibold text-simonBlue">Strategic Intelligence Chat</h2>
        <label className="text-xs text-muted-foreground flex items-center gap-2 ml-auto">
          Model
          <select
            className="border rounded px-2 py-1 text-sm bg-white"
            value={model}
            disabled={loading}
            onChange={(e) => setModel(e.target.value)}
          >
            {models.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
        </label>
      </div>
      {modelErr ? (
        <p className="text-xs text-amber-700 px-6 py-1 bg-amber-50 border-b">{modelErr}</p>
      ) : null}

      <ScrollArea className="flex-1 p-6">
        <div className="max-w-4xl mx-auto space-y-6">
          {messages.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
              <Card
                className={`max-w-[80%] p-4 ${msg.role === "user" ? "bg-simonBlue text-white" : "bg-white"}`}
              >
                <div
                  className={`prose prose-sm max-w-none ${msg.role === "user" ? "prose-invert" : ""}`}
                >
                  {msg.role === "assistant" && loading && i === messages.length - 1 && !msg.content ? (
                    <span className="text-muted-foreground animate-pulse">Thinking…</span>
                  ) : (
                    <Markdown>{msg.content || " "}</Markdown>
                  )}
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
            onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && void handleSend()}
            placeholder="Query your strategic data..."
            className="flex-1 border-simonBlue/20 focus-visible:ring-simonBlue"
            disabled={loading}
          />
          <Button
            onClick={() => void handleSend()}
            disabled={loading}
            className="bg-dandelionYellow text-simonBlue hover:bg-simonBlue hover:text-white transition-colors"
          >
            <Send className="h-4 w-4 mr-2" />
            Analyze
          </Button>
        </div>
      </div>
    </div>
  );
}
