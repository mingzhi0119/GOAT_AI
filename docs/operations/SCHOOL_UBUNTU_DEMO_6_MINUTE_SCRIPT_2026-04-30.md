# GOAT AI School Ubuntu Demo - Detailed 6 Minute Script / 六分钟详细演讲稿

Reference style: `examples/Transcript for demo.docx`

This version is intentionally detailed. It follows the previous demo-transcript style, but every segment states exactly what to do on screen and what to say aloud. The recommended rhythm is about 6 minutes if spoken at normal demo speed. If the room is slow to respond or the model streams slowly, skip the optional Workbench/search live step and keep the Theme + local runtime + upload/chart + ops proof as the core story.

## Pre-Demo Setup / 演示前准备

**Do / 做什么:** Before the presentation starts, prepare the browser and terminal.

- Open the deployed school frontend page, for example the `/mingzhi/` route.
- Keep one terminal open at the project root.
- Pre-type these commands so you can press Enter instead of typing live:

```bash
curl -sS http://127.0.0.1:62606/api/health
curl -sS http://127.0.0.1:62606/api/ready
curl -sS http://127.0.0.1:62606/api/system/runtime-target
python -m tools.ops.post_deploy_check --base-url http://127.0.0.1:62606
```

- Prepare one small PDF, Markdown, or CSV file for upload.
- If web search is part of the live demo, either configure `SERPER_API_KEY` in `.env.school-ubuntu`, or be ready to say the app will automatically use DuckDuckGo fallback.
- In the app, make sure you know where `Options -> Appearance` is. Theme is now a main talking point.

## 0:00-0:35 Opening / 开场定位

**Do / 做什么:** Show the full GOAT AI interface first. Do not start with terminal commands. Let the audience see the product shell: sidebar, chat area, top bar, model selector, and input composer.

**Say / 说什么:**

“Good morning, everyone. Today I’m going to demonstrate GOAT AI. I want to frame it clearly: this is not just a simple chatbot page. This project is a school-deployable AI assistant with a local model runtime, a theme and branding system, streaming chat, file-aware retrieval, chart and artifact generation, optional web search, and operational readiness checks.

The reason I built it this way is that a real AI product needs more than a prompt box. It needs identity, runtime control, user experience polish, file workflows, and deployment proof. So in this demo, I’ll show both what the user can do and what the system proves technically.”

## 0:35-1:45 Theme System / 主题系统：Standard、UR、清华

**Do / 做什么:** Open `Options -> Appearance`. Slowly point to the controls. Switch between Theme mode if useful, then show `Theme style` cards: `Classic`, `URochester`, and `THU`. Click or point to `URochester`, then `THU`, then return to the style you want for the rest of the demo.

**Say / 说什么:**

“I want to start with Theme, because this project recently strengthened appearance from a basic light-dark toggle into a real theme system.

There are three product skins here. The first is `Classic`, which is the standard GOAT AI baseline. It is neutral, clean, and close to a general productivity assistant. The second is `URochester`, which uses the University of Rochester style direction: navy and dandelion yellow, with Simon Business School branding in the sidebar footer. The third is `THU`, the Tsinghua theme, using deep Tsinghua purple and a gold accent, with a Tsinghua logo in the sidebar footer.

This is not only cosmetic. The theme system controls semantic tokens across the app: main background, sidebar, chat surface, user bubble, assistant bubble, borders, links, code blocks, and composer controls. The active accent color is reused consistently in the send button, selected state, user message bubble, links, and highlights.

It also connects to the assistant experience. When there is no explicit custom system prompt override, the frontend can send `theme_style` with the chat request, and the backend uses that to choose a matching default persona: standard general-purpose for `Classic`, business-oriented Simon/Rochester for `URochester`, and research-oriented Tsinghua for `THU`.

It also has theme mode: Light, Dark, and System. System follows the operating system preference. Dark mode is handled carefully so school logos remain readable. For example, Tsinghua uses a reversed logo treatment in dark mode.

There are also power-user controls: accent presets, custom accent color, UI font, code font, contrast strength, and translucent sidebar. Changes apply immediately to the live shell, and the preference is stored locally in the browser. The important engineering point is that components do not hardcode random colors. They consume semantic CSS variables from a centralized appearance registry. That makes the product skin extensible and safer to maintain.”

**Optional short Chinese explanation if needed / 可选中文补充:**

“这里我想强调一下，Theme 不是简单换背景色。它是一个 token-driven appearance system。标准主题负责通用场景，UR 主题负责 Rochester/Simon branding，清华主题负责学校演示场景。它会影响 logo、accent、气泡、sidebar、代码块、对比度和字体，也会在没有自定义 system prompt 时影响默认助手 persona，而且设置保存在本地，不需要改后端。”

## 1:45-2:30 School Local Runtime / 学校本地 AI 运行时

**Do / 做什么:** Close Appearance. Open the model dropdown. If it is smooth, briefly show the terminal command for runtime target, or keep this as spoken explanation and save terminal for the ops section.

**Say / 说什么:**

“Next is the runtime. In the school Ubuntu profile, the app is designed for `GOAT_DEPLOY_MODE=1`. The backend talks to a local Ollama runtime at `127.0.0.1:11435`. That means the model list comes from the server environment, and the school can run its own model stack instead of relying only on a cloud API.

This matters for privacy, cost, and control. Privacy, because school files and prompts can stay in the school-controlled environment. Cost, because local inference avoids per-query API charges for supported workloads. Control, because the deployment profile is explicit: Windows development, normal local deployment, and school Ubuntu deployment do not require source-code edits to switch behavior. They are driven by environment configuration.”

## 2:30-3:15 Streaming Chat / 流式聊天与会话体验

**Do / 做什么:** Send this prompt:

```text
Explain Porter's Five Forces in 5 concise bullet points.
```

Point to the answer as it streams. Point to history/sidebar after completion.

**Say / 说什么:**

“Now I’ll run a basic chat request. The response streams live instead of waiting for one big final answer. Internally, the backend can emit typed server-sent events: thinking, answer token, chart specification, artifact, error, and done. That structure lets the frontend render different output types cleanly.

For the user, the experience is simple: ask a question and see the response appear immediately. For the system, the advantage is that the UI can handle richer assistant behavior without becoming a fragile text parser. The session is also persisted, so previous conversations can be reopened from the sidebar.”

## 3:15-4:05 Upload And RAG / 文件上传与检索增强

**Do / 做什么:** Upload the prepared file. Then send:

```text
Summarize this document and cite the key evidence.
```

If time allows, ask one follow-up:

```text
What are the three most important takeaways for a presentation?
```

**Say / 说什么:**

“The next feature is file-grounded work. In many school and business scenarios, the user is not asking general trivia. They have a specific case, memo, dataset, syllabus, article, or exported CSV. This app can ingest files and use retrieval-backed context so the assistant answers from the uploaded material.

That changes the value proposition. Instead of saying, ‘Here is what the model generally knows,’ the workflow becomes, ‘Here is my material, help me understand it, summarize it, and turn it into something useful.’ Follow-up questions can stay in the same session, so the user can build on the uploaded context.”

## 4:05-4:45 Charts And Artifacts / 图表与可下载产物

**Do / 做什么:** Send this prompt:

```text
Create a simple chart comparing revenue for Jan, Feb, and Mar: 10, 15, 12.
```

Point to the chart area. If an artifact or download affordance appears, point to it as well.

**Say / 说什么:**

“GOAT AI also goes beyond plain text. A response can include a structured chart event, and the frontend renders it visually. The same architecture supports downloadable artifacts, such as a Markdown summary.

This is important because real users often want an output, not only a conversation. They may want a chart, a memo, a cleaned summary, or a reusable artifact. So the assistant starts to feel more like a workflow tool than a chat-only toy.”

## 4:45-5:25 Workbench And Web Search / Workbench 与网页搜索

**Do / 做什么:** If Workbench is enabled, briefly show the Workbench task surface. If search/network is stable, ask:

```text
Search the latest news about AI deployment best practices and cite sources.
```

If search is not stable, do not force it. Explain the capability and the fallback behavior.

**Say / 说什么:**

“For more advanced workflows, the project has a Workbench layer. It is intentionally bounded: plan, browse, deep research, and canvas workflows can create task state, event timelines, and reusable outputs. I describe it as controlled research assistance, not an unlimited autonomous agent.

The web search path is also stronger now. Serper is the default provider for Google-backed search results. But for the school demo, we fixed the key reliability issue: Serper is no longer a startup hard dependency. If `SERPER_API_KEY` is missing, or Serper times out, returns an HTTP error, hits rate limit, or returns a malformed response, the provider automatically falls back to DuckDuckGo. If both providers fail, the app says search is unavailable and does not invent citations.

That is the behavior I want in a live demo: useful when the network works, graceful when an external provider is unavailable.”

## 5:25-5:55 Operations Proof / 运维证明

**Do / 做什么:** Switch to terminal. Run or show these commands quickly:

```bash
curl -sS http://127.0.0.1:62606/api/health
curl -sS http://127.0.0.1:62606/api/ready
curl -sS http://127.0.0.1:62606/api/system/runtime-target
python -m tools.ops.post_deploy_check --base-url http://127.0.0.1:62606
```

**Say / 说什么:**

“The final proof is operations. For a live school environment, I need to know more than ‘the webpage opened.’ I need to know the backend is healthy, the model runtime is reachable, the selected deployment target is correct, and chat streaming works after deploy.

That is why the project includes health and ready endpoints, runtime-target introspection, metrics, post-deploy checks, rollback documentation, and a dedicated school Ubuntu deploy path. The school deploy wrapper now also loads `.env` and `.env.school-ubuntu` before the fallback process, so demo-critical environment variables are preserved even if deployment falls back from systemd to nohup.”

## 5:55-6:20 Closing / 结尾

**Do / 做什么:** Return to the app screen. Show the themed interface, a chat answer, and generated output if available.

**Say / 说什么:**

“So the complete story is this: GOAT AI combines a polished theme and branding system, local school runtime, streaming chat, file-grounded answers, charts, artifacts, bounded research workflows, resilient web search, and deployment proof.

My main point is that this project is not only about asking a model questions. It is about building the product layer and engineering layer around the model so it can be used in a real school environment. Thank you.”

## If You Need To Stretch To 7 Minutes / 如果需要拉长到七分钟

Use this extra paragraph after the Theme section:

“From an engineering perspective, the theme system also shows how the project is structured. The frontend stores appearance settings in `localStorage`, migrates older light-dark settings, and applies tokens at the document root before React fully renders, which helps avoid first-paint flicker. That is the kind of detail that matters when moving from a prototype to a product-like app.”

Use this extra paragraph after the Ops section:

“Another important point is that the deployment profile is honest about dependencies. Features such as Workbench, code sandbox, and web search are behind explicit runtime readiness or operator configuration. If something is unavailable, the app should say so clearly instead of silently pretending it worked.”

## Predicted Q&A / 预测问答

**Q1: Why start with Theme instead of model capability?**  
“Because Theme is part of product readiness. A school demo needs a credible identity layer. The standard theme is the general product baseline, URochester maps to Rochester/Simon branding, and THU maps to the Tsinghua-style school presentation path.”

**Q2: Is the theme system only visual?**  
“No. It affects root semantic tokens, sidebar branding, accent behavior, light/dark/system mode, fonts, contrast, and local persistence. It also connects to default assistant persona through `theme_style` when no explicit system prompt override is configured.”

**Q3: Why not just use ChatGPT?**  
“ChatGPT is strong, but this project emphasizes controllable deployment, local runtime options, school-specific theming, file workflows, and operational proof. The goal is not to beat every general model; the goal is to build a school-deployable AI system.”

**Q4: What happens if Serper API key is missing?**  
“The backend still starts. Default `serper` mode falls back to DuckDuckGo when the key is missing or Serper is unavailable. If the operator wants no public web search, they explicitly set `GOAT_WORKBENCH_WEB_PROVIDER=disabled`.”

**Q5: What if Ollama is down?**  
“The readiness checks and post-deploy check should catch that before the presentation. The school profile expects local Ollama on `127.0.0.1:11435`, so I verify that before demoing chat.”

**Q6: Is this production-ready for a whole school?**  
“It is demo-ready as a controlled school deployment profile. For full campus-scale production, the next work would be authentication policy, rate limiting, stronger multi-user persistence, monitoring dashboards, and capacity planning.”

**Q7: What is the strongest technical part?**  
“The strongest part is the boundary design: appearance tokens, runtime config, streaming events, retrieval, artifacts, Workbench tasks, search provider fallback, and ops checks are separated enough to test and reason about.”

## Quick Tips / 现场提示

| Moment | Do / 做什么 | Say / 说什么 |
| --- | --- | --- |
| Opening | Show the full app, not terminal | “I’ll show product experience first, then prove runtime.” |
| Theme | Open Appearance and switch Classic -> URochester -> THU | “This is a product skin system, not just light/dark.” |
| UR Theme | Point at navy/yellow and Simon/Rochester logo | “UR theme carries Rochester/Simon identity.” |
| THU Theme | Point at purple/gold and Tsinghua logo | “THU theme is designed for this school-style presentation.” |
| Chat | Use a short prompt | “Streaming makes the app feel live and gives typed events to the UI.” |
| Upload | Use a small file | “This makes the assistant file-aware, not just model-memory-based.” |
| Chart | Use tiny numbers | “The chart is generated from structured model output.” |
| Search | Only demo if network is stable | “Serper is default; DuckDuckGo is fallback; disabled is explicit.” |
| Terminal | Keep commands pre-typed | “These endpoints prove the deployment is alive and correctly targeted.” |
