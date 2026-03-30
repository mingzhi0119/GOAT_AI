/** Ollama HTTP API — same contract as Streamlit app.py */

function getBaseUrl(): string {
  const env = import.meta.env.VITE_OLLAMA_BASE_URL;
  if (env && env.trim()) {
    return env.replace(/\/$/, "");
  }
  // Dev: Vite proxy /ollama → 127.0.0.1:11434. Prod: expect nginx (or similar) to proxy same path.
  return "/ollama";
}

export function getDefaultModel(): string {
  return import.meta.env.VITE_OLLAMA_MODEL ?? "llama3:latest";
}

export async function fetchOllamaModels(): Promise<string[]> {
  const base = getBaseUrl();
  const ac = new AbortController();
  const t = window.setTimeout(() => ac.abort(), 8000);
  let res: Response;
  try {
    res = await fetch(`${base}/api/tags`, { signal: ac.signal });
  } finally {
    window.clearTimeout(t);
  }
  if (!res.ok) {
    throw new Error(`Ollama /api/tags: ${res.status}`);
  }
  const data = (await res.json()) as { models?: { name: string }[] };
  const names = (data.models ?? []).map((m) => m.name);
  return names.length ? names : [getDefaultModel()];
}

export async function* streamGenerate(
  model: string,
  prompt: string
): AsyncGenerator<string, void, undefined> {
  const base = getBaseUrl();
  const res = await fetch(`${base}/api/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ model, prompt, stream: true }),
  });
  if (!res.ok) {
    const t = await res.text();
    throw new Error(t || `Ollama error ${res.status}`);
  }
  const reader = res.body?.getReader();
  if (!reader) {
    throw new Error("Empty response body");
  }
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";
    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed) continue;
      const chunk = JSON.parse(trimmed) as { response?: string; done?: boolean };
      if (chunk.response) {
        yield chunk.response;
      }
    }
  }
  const rest = buffer.trim();
  if (rest) {
    const chunk = JSON.parse(rest) as { response?: string };
    if (chunk.response) {
      yield chunk.response;
    }
  }
}
