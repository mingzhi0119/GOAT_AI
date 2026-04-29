# GOAT AI School Ubuntu Demo Script - English Professional Version

## 6-8 Minute Live Demo Script, with Presenter Notes, Fallback Lines, and Q&A

**Recommended use:** English live presentation. This version is written as a speaker-ready script, not a literal translation. It keeps the technical story accurate but makes the delivery smoother, more professional, and easier to perform during a demo.

**Demo date:** 2026-04-30  
**Target environment:** School Ubuntu deployment profile  
**Main route:** Product identity -> local runtime -> streaming chat -> file-grounded retrieval -> charts/artifacts -> Workbench/search -> operations proof

---

## 1. Core Positioning

### One-sentence product positioning

GOAT AI is not just a chatbot UI. It is a school-deployable AI assistant system that combines a branded product shell, local model runtime control, streaming chat, file-aware retrieval, structured outputs, optional web research, and deployment health checks.

### Main message for the audience

The strongest point of the project is not only that the model can answer prompts. The stronger story is that GOAT AI builds the product layer and the engineering layer around the model so it can be demonstrated, deployed, and verified in a school-controlled environment.

### Demo posture

Use the phrase **controlled school demo deployment**. This is a stronger and safer claim than saying it is fully campus-production-ready. For full production use, the next steps would be authentication, role-based access control, rate limiting, monitoring dashboards, multi-user capacity planning, and a clearer data governance policy.

---

## 2. Current State Snapshot

| Area | How to describe it in the demo |
| --- | --- |
| Product shell | React single-page app with sidebar, chat area, top bar, model selector, input composer, and session history. |
| Theme and branding | Three product skins: Classic, URochester, and THU. The system uses semantic appearance tokens, not random hardcoded colors. |
| Runtime | FastAPI backend connects to a local Ollama runtime in the school Ubuntu profile. The runtime target is environment-driven. |
| Streaming | Chat responses stream over typed server-sent events: thinking, token, chart_spec, artifact, error, and done. |
| Files and RAG | Uploaded files can become knowledge documents and be used for retrieval-backed answers. |
| Charts and artifacts | The assistant can return structured chart events and downloadable artifacts instead of only plain text. |
| Workbench and search | Workbench is a bounded research/workflow layer. Search can use Serper, fall back to DuckDuckGo, or be explicitly disabled. |
| Operations proof | Health, readiness, runtime-target, metrics, and post-deploy checks prove the service is actually deployable. |

---

## 3. Pre-Demo Checklist

### Browser setup

- Open the deployed school frontend page, for example the `/mingzhi/` route.
- Keep the browser full screen.
- Start with the full product shell visible: sidebar, chat panel, top bar, model selector, and composer.
- Know exactly where `Options -> Appearance` is.
- Decide which theme you want to end on after switching through the theme options.

### Terminal setup

Keep one terminal open at the project root. Pre-type these commands so you only need to press Enter during the demo:

```bash
curl -sS http://127.0.0.1:62606/api/health
curl -sS http://127.0.0.1:62606/api/ready
curl -sS http://127.0.0.1:62606/api/system/runtime-target
python -m tools.ops.post_deploy_check --base-url http://127.0.0.1:62606
```

### Demo assets

- Prepare one small PDF, Markdown, DOCX, or CSV file for upload.
- If web search is part of the live demo, verify the `SERPER_API_KEY` or be ready to explain DuckDuckGo fallback.
- For the web-search demo, prefer official OpenAI release sources first, then business/tech media as supporting citations.
- If the network is unstable, do not force a live search. Explain the architecture and fallback behavior instead.

### Live prompts to copy

```text
Explain Porter's Five Forces in 5 concise bullet points.
```

```text
Summarize this document and cite the key evidence.
```

```text
What are the three most important takeaways for a presentation?
```

```text
Create a simple chart comparing revenue for Jan, Feb, and Mar: 10, 15, 12.
```

```text
Search the latest news about GPT-5.5. When was it released, and what are the business implications for students, analysts, and managers? Cite sources.
```

---

## 4. Minute-by-Minute Speaker Script

### 0:00-0:40 - Opening: show the product before showing the terminal

**Demo goal:** Establish that GOAT AI is a deployable AI product prototype, not just a prompt box.

**Screen action:** Show the full GOAT AI interface. Do not start with terminal commands. Let the audience see the sidebar, chat area, model selector, and composer.

**Speaker script:**

Good morning, everyone. Today I am going to demonstrate GOAT AI.

I want to frame the project clearly before I click anything. GOAT AI is not just a simple chatbot page. It is a school-deployable AI assistant system. It combines a branded product interface, a local model runtime, streaming chat, file-aware retrieval, chart and artifact generation, optional web research, and operational readiness checks.

The reason I built it this way is that a real AI product needs more than a prompt box. It needs an identity, a runtime boundary, a usable workflow, and a way to prove that the deployment is actually healthy.

So in this demo, I will show two things at the same time: what the user can do, and what the system proves technically.

**Transition:**

I will start with the interface and theme system, because in a school demo the first impression is not a model parameter. It is whether the system looks credible and intentional.

---

### 0:40-2:05 - Theme system: from light/dark mode to branded product skins

**Demo goal:** Show Classic, URochester, and THU. Explain that the theme system is product infrastructure, not just decoration.

**Screen action:** Open `Options -> Appearance`. Point to theme mode, theme style, accent controls, font controls, contrast, and translucent sidebar. Switch from Classic to URochester to THU. End on the theme you want to use for the rest of the demo.

**Speaker script:**

I will open the Appearance panel first. This part of the project recently moved from a simple light/dark toggle into a real theme system.

There are three product skins here. **Classic** is the standard GOAT AI baseline: neutral, clean, and suitable for a general productivity assistant. **URochester** uses the University of Rochester and Simon Business School direction, especially the navy and dandelion yellow identity. **THU** uses a Tsinghua-style visual direction with deep purple and gold, plus school branding in the sidebar footer.

The important point is that this is not only cosmetic. The frontend uses a token-driven appearance system. Components do not randomly hardcode colors. They consume semantic tokens for the main background, sidebar, chat surface, user bubble, assistant bubble, borders, links, code blocks, and composer controls.

That means if I change the theme, the whole product shell updates consistently. The send button, selected states, user message bubble, links, and highlights reuse the active accent color instead of drifting into unrelated styles.

The system also supports Light, Dark, and System mode. System follows the operating system preference. Dark mode is handled carefully so school logos stay readable, instead of simply inverting everything and hoping it looks fine.

There is also a more subtle connection to the assistant itself. When the user does not provide a custom system prompt, the frontend can send `theme_style` with the chat request. The backend can then choose a matching default persona: a standard assistant for Classic, a slightly business-oriented Simon/Rochester assistant for URochester, and a more research-oriented assistant for THU.

So this theme system is doing three jobs: it gives the product a brand identity, it keeps the frontend maintainable, and it can influence the default assistant experience.

**Transition:**

Now that we have seen the product identity, the next question is where the AI actually runs and how the school controls it.

**Fallback line if theme switching is slow:**

Even if I do not switch every theme live, the key point is that these settings are stored locally and applied through semantic tokens, so the theme is part of the product architecture rather than a one-off visual patch.

---

### 2:05-2:50 - School-local runtime: control, privacy, and deployment separation

**Demo goal:** Explain the school Ubuntu profile and local Ollama runtime without getting stuck in terminal details too early.

**Screen action:** Close Appearance. Open the model selector. If it is smooth, briefly show that models come from the server policy. Save terminal proof for the operations section.

**Speaker script:**

The next part is the runtime.

In the school Ubuntu profile, GOAT AI is designed to use a local Ollama runtime. The backend talks to the model service on the school machine, using the deployment profile rather than a hardcoded source-code change.

This matters for three reasons.

First, **privacy**: school files and prompts can stay in a school-controlled environment for supported workloads. Second, **cost control**: local inference avoids per-query cloud API cost for the models the school chooses to run. Third, **operational control**: Windows development, local testing, and school Ubuntu deployment can be separated by environment configuration instead of branching the codebase.

So the model selector is not just a dropdown. It reflects a deployment policy: which models are allowed, which runtime is reachable, and what the current environment is prepared to support.

**Transition:**

With the runtime in place, I will now show the basic user experience: a streaming chat request.

---

### 2:50-3:35 - Streaming chat: fast feedback and typed events

**Demo goal:** Show that chat streams live and that the backend has structured event types.

**Screen action:** Send this prompt:

```text
Explain Porter's Five Forces in 5 concise bullet points.
```

Point to the response as it streams. After completion, point to session history/sidebar if visible.

**Speaker script:**

Now I will run a simple chat request.

What you should notice is that the answer streams live. The user does not wait for one big final response. As tokens arrive, the UI updates immediately, which makes the assistant feel responsive even when the model is still generating.

Technically, this is not just raw text being dumped into the browser. The backend can emit typed server-sent events: thinking, answer token, chart specification, artifact, error, and done. That event structure lets the frontend render different output types cleanly without relying on fragile text parsing.

For the user, the experience is simple: ask a question and watch the answer appear. For the system, the advantage is that richer assistant behavior can be added without breaking the chat UI.

The session is also persisted, so previous conversations can be reopened from the sidebar instead of disappearing after refresh.

**Transition:**

A general chat answer is useful, but most school and business work is not general trivia. Users usually bring their own files. That is the next workflow.

**Fallback line if the model is slow:**

If the model takes a few seconds, that actually shows why streaming matters. The user still sees progress instead of staring at a frozen page.

---

### 3:35-4:35 - File upload and retrieval-backed work

**Demo goal:** Show that GOAT AI can work from user-provided material, not only model memory.

**Screen action:** Upload the prepared PDF, Markdown, DOCX, or CSV file. Then send:

```text
Summarize this document and cite the key evidence.
```

If time allows, follow with:

```text
What are the three most important takeaways for a presentation?
```

**Speaker script:**

The next feature is file-grounded work.

In real school and business scenarios, the user often has a specific document: a syllabus, a case memo, a research article, meeting notes, or a dataset. They are not asking, "What does the model generally know?" They are asking, "Here is my material. Help me understand it and turn it into something useful."

GOAT AI supports that workflow by registering the upload as a knowledge document and using retrieval-backed context in later answers. The chat request can reference `knowledge_document_ids`, so the answer is grounded in the uploaded material rather than only in the model's general training.

This changes the value proposition. The assistant becomes a reading, summarizing, and transformation tool for the user's own materials. A student could summarize course notes. A team could extract action items from a memo. A presenter could turn a document into key takeaways.

The follow-up question is important too. Because the document stays connected to the session, I can ask for the top three presentation takeaways without uploading again or restating the whole context.

**Transition:**

Once the assistant can understand the user's material, the next step is producing outputs that are more useful than plain text.

**Fallback line if upload is slow:**

If the upload takes longer than expected, I would describe the mechanism rather than waiting: the upload becomes a knowledge document, and the next chat turn can use that document for retrieval-backed answering.

---

### 4:35-5:15 - Charts and artifacts: output beyond plain text

**Demo goal:** Demonstrate structured visual output and downloadable artifacts.

**Screen action:** Send this prompt:

```text
Create a simple chart comparing revenue for Jan, Feb, and Mar: 10, 15, 12.
```

Point to the chart. If a downloadable artifact appears, point to the download affordance.

**Speaker script:**

GOAT AI also goes beyond plain text.

Here I am asking for a simple chart. The important detail is that the assistant can return a structured chart event, and the frontend renders it visually. This is different from just writing a Markdown table and asking the user to imagine a chart.

The same architecture supports downloadable artifacts, such as a Markdown summary or reusable generated output. That matters because real users often want an object at the end of the conversation: a chart, a memo, a cleaned summary, a report draft, or something they can download and continue editing.

So the assistant starts to feel less like a chat toy and more like a workflow tool.

**Transition:**

For more advanced workflows, GOAT AI also has a bounded Workbench and optional web search path.

**Fallback line if the chart does not render:**

If the chart UI does not appear, I would still explain the event model: the backend can emit a `chart_spec` event, and the frontend is designed to render that structured event rather than scrape it from plain text.

---

### 5:15-5:55 - Workbench and web search: bounded research, not an uncontrolled agent

**Demo goal:** Explain Workbench and search reliability without overclaiming full autonomy.

**Screen action:** If Workbench is enabled, briefly show the Workbench task surface. If network is stable, send:

```text
Search the latest news about GPT-5.5. When was it released, and what are the business implications for students, analysts, and managers? Cite sources.
```

If network is not stable, skip the live query and explain the fallback policy.

**Speaker script:**

GOAT AI also includes a Workbench layer for more advanced workflows. I describe this as **bounded research assistance**, not an unlimited autonomous agent.

Workbench tasks can support planning, browsing, deeper research, and canvas-style outputs. The important design choice is that these workflows are explicit and capability-gated. If a feature is disabled by the operator or unavailable on the host, the system should say so clearly instead of pretending it worked.

The web search path follows the same idea. Serper can be used for Google-backed results. But the school demo path is more robust now: Serper is not a startup blocker. If the Serper key is missing, or Serper times out, returns an HTTP error, hits a rate limit, or returns malformed data, the provider can fall back to DuckDuckGo.

For a Business School audience, I use GPT-5.5 as the search topic because it is current, relevant, and easy to connect to business workflows. The answer should first identify the release date, then translate the news into implications for three audiences: students, analysts, and managers. The key takeaway is that newer AI models are moving from simple conversation toward more agentic work: research synthesis, coding and data analysis support, workflow automation, and higher-level managerial oversight.

If the model cites media sources such as CNBC, TechCrunch, or Fortune, I will still frame official OpenAI release information as the preferred primary source when available, with media coverage as supporting evidence.

If both providers fail, the assistant should say search is unavailable and avoid inventing citations. That is exactly the behavior I want in a live school demo: useful when the network works, graceful when an external dependency fails.

**Transition:**

The last part of the demo is operations proof. I do not want to only show that the page opened. I want to show that the deployment is actually healthy.

**Fallback line if search is disabled:**

For this environment, web search may be disabled by configuration. That is not a failure of the app shell; it is an explicit operator decision. The UI should reflect availability instead of assuming every advanced feature is always enabled.

---

### 5:55-6:40 - Operations proof: health, readiness, runtime target, and post-deploy check

**Demo goal:** Prove that the app is deployed and reachable, not merely visually loaded.

**Screen action:** Switch to terminal. Run or show these commands:

```bash
curl -sS http://127.0.0.1:62606/api/health
curl -sS http://127.0.0.1:62606/api/ready
curl -sS http://127.0.0.1:62606/api/system/runtime-target
python -m tools.ops.post_deploy_check --base-url http://127.0.0.1:62606
```

**Speaker script:**

The final proof is operations.

For a school deployment, it is not enough to say, "The webpage opened." I need to know that the backend is healthy, the database check passes, the model runtime is reachable when required, the selected deployment target is correct, and chat streaming works after deployment.

That is why the project includes health and readiness endpoints, runtime-target introspection, Prometheus-style metrics, post-deploy checks, rollback documentation, and a dedicated school Ubuntu deployment path.

This is also where the school profile matters. Demo-critical environment variables can live in `.env.school-ubuntu`, and the deploy path is designed around that profile. So the demo is not relying on random local machine state. It has a repeatable deployment story.

**Transition:**

I will switch back to the product screen to close the demo from the user's point of view.

**Fallback line if one command fails:**

If one check fails during a live demo, I would not hide it. I would say: this is why the checks exist. They make runtime problems visible before users depend on the system.

---

### 6:40-7:05 - Closing: bring the story together

**Demo goal:** Summarize the product and engineering story in one polished close.

**Screen action:** Return to the app screen. Show the themed interface, the chat answer, and the generated chart or upload result if available.

**Speaker script:**

So the complete story is this: GOAT AI combines a polished theme and branding system, a local school runtime, streaming chat, file-grounded answers, charts, downloadable artifacts, bounded research workflows, resilient search behavior, and deployment proof.

My main point is that this project is not only about asking a model questions. It is about building the product layer and engineering layer around the model so it can be used in a real school environment.

Thank you.

---

## 5. Six-Minute Compressed Version

Use this version if the room is strict about timing.

### 0:00-0:30 - Opening

Good morning, everyone. Today I am demonstrating GOAT AI. I want to frame it clearly: this is not just a chatbot page. It is a school-deployable AI assistant system with a branded interface, local runtime control, streaming chat, file-aware retrieval, structured outputs, optional web research, and deployment health checks.

### 0:30-1:40 - Theme

I will start with Appearance. GOAT AI has three product skins: Classic, URochester, and THU. This is not just cosmetic. The frontend uses semantic appearance tokens for backgrounds, chat surfaces, bubbles, borders, links, code blocks, and controls. That makes the product skin consistent and maintainable.

The theme can also connect to the assistant persona. When there is no custom system prompt, the frontend can send `theme_style`, and the backend can choose a default persona that matches Classic, Rochester/Simon, or Tsinghua-style use cases.

### 1:40-2:20 - Runtime

In the school Ubuntu profile, GOAT AI uses a local Ollama runtime. This gives the school more control over privacy, cost, and deployment behavior. The model list and capabilities come from the backend policy rather than being hardcoded into the UI.

### 2:20-3:00 - Streaming chat

Here I will ask a basic question. The response streams live, so the user sees progress immediately. Internally, the backend can emit typed events such as thinking, token, chart specification, artifact, error, and done. That makes the frontend more reliable than a plain text parser.

### 3:00-3:50 - Upload and RAG

Next, I will upload a file and ask the assistant to summarize it. This is important because real users usually bring their own material: a case, memo, syllabus, article, or dataset. GOAT AI can register the upload as a knowledge document and use retrieval-backed context in later chat turns.

### 3:50-4:30 - Chart and artifacts

GOAT AI can also produce structured outputs. Here I ask for a simple chart. The frontend can render a structured chart event, and the same architecture supports downloadable artifacts. So the result is not only a conversation; it can become an output the user reuses.

### 4:30-5:10 - Workbench/search

For advanced workflows, GOAT AI has a bounded Workbench layer. It is controlled research assistance, not an unlimited autonomous agent. Search can use Serper, fall back to DuckDuckGo, or be disabled by the operator. If search fails, the assistant should say so instead of inventing citations.

### 5:10-5:45 - Ops proof

Finally, I will show operations proof. Health, readiness, runtime target, metrics, and post-deploy checks prove that the service is alive, correctly targeted, and ready for the demo environment. This matters because a school deployment needs verifiability, not only a nice webpage.

### 5:45-6:00 - Closing

GOAT AI combines product polish with engineering boundaries: theme, local runtime, streaming, files, charts, Workbench, search fallback, and deploy checks. The goal is to build the system around the model so it can be used in a real school setting. Thank you.

---

## 6. Eight-Minute Expanded Additions

Use these paragraphs only if you have extra time.

### Add after Theme

From an engineering perspective, the appearance system also demonstrates how the frontend is structured. Settings persist in `localStorage`, older light/dark settings can be migrated into the new model, and the root token set is applied early to reduce first-paint flicker. These are small details, but they are the difference between a prototype that looks good once and a product shell that stays maintainable.

### Add after Runtime

Another reason the runtime profile matters is debugging. If the system fails, I do not want to guess whether the frontend, backend, model runtime, or environment file is the problem. The runtime-target endpoint and post-deploy check create a clearer boundary, which makes the demo easier to operate and the system easier to maintain.

### Add after Upload/RAG

The RAG design is also safer from a user-experience point of view. Instead of permanently mixing every upload into a giant hidden memory, the request can explicitly carry the relevant document identifiers. That makes the relationship between the user turn and the knowledge source easier to reason about.

### Add after Workbench/Search

The Workbench layer is deliberately not presented as magic autonomy. Long-running AI systems need boundaries: which sources are available, which tools are enabled, which outputs are durable, and what happens if a provider is unavailable. I would rather have a bounded system that fails honestly than an impressive-looking system that silently fabricates evidence.

---

## 7. Live Demo Fallback Playbook

### If the model is slow

Use this line:

The delay is exactly why streaming is useful. The UI can show progress while the model is still generating instead of blocking the user behind a blank screen.

### If upload or retrieval is slow

Use this line:

I will describe the workflow while it processes: the upload is registered as a knowledge document, and later chat turns can pass that document ID to get retrieval-backed answers.

### If search fails

Use this line:

This is the failure mode the project is designed to handle. Search should be useful when available, but if providers fail, the assistant should report that clearly instead of inventing citations.

### If Workbench is disabled

Use this line:

In this deployment, Workbench may be disabled by operator configuration. That is intentional capability gating, not a broken button. The system should expose advanced workflows only when the environment supports them.

### If a health check fails

Use this line:

This is exactly why these checks are part of the demo. They make deployment problems visible and actionable instead of hiding them behind a page that happens to load.

### If you run out of time

Skip live web search first. Then skip the second upload follow-up. Keep these four pillars: Theme, local runtime, streaming chat, and operations proof.

---

## 8. Predicted Q&A

### Q1. Why start with Theme instead of model capability?

Because the demo is about a deployable product, not only raw model intelligence. A school environment needs a credible identity layer. The theme system shows branding, maintainability, accessibility concerns, and even persona selection through `theme_style`.

### Q2. Is the theme system only visual?

No. It affects semantic UI tokens, sidebar branding, accent behavior, light/dark/system mode, fonts, contrast, local persistence, and default assistant persona selection when there is no explicit system prompt override.

### Q3. Why not just use ChatGPT?

ChatGPT is very strong as a general assistant. GOAT AI has a different goal: controlled deployment, local runtime options, school-specific branding, file workflows, structured outputs, and operational proof. The goal is not to beat every cloud model. The goal is to build a school-deployable AI system around the model.

### Q4. What happens if the Serper API key is missing?

The backend should still start. In the default Serper mode, missing or unavailable Serper can fall back to DuckDuckGo. If the operator wants no public web search, they can explicitly disable the web provider.

### Q5. What if Ollama is down?

The readiness and post-deploy checks should catch that before the presentation. The school profile expects a local Ollama runtime, so I verify that before relying on chat.

### Q6. Is this production-ready for an entire school?

It is demo-ready as a controlled school deployment profile. For full campus-scale production, the next work would include authentication, authorization, rate limiting, monitoring dashboards, multi-user persistence, and capacity planning.

### Q7. What is the strongest technical part?

The strongest part is the boundary design. Appearance tokens, runtime configuration, streaming events, retrieval, artifacts, Workbench tasks, search fallback, and ops checks are separated enough to test, explain, and maintain.

### Q8. How does file upload differ from normal chat context?

Normal chat context is just conversation text. The upload path can register a document, ingest it, and pass document identifiers into later chat turns. That makes the answer more grounded in the uploaded material.

### Q9. Why use typed SSE events?

Typed events let the frontend treat different outputs differently. A token is rendered as answer text, a chart spec becomes a visual chart, an artifact becomes a downloadable file, and errors can be displayed cleanly. That is more reliable than parsing a single text stream.

### Q10. What would you improve next?

I would focus on production hardening: authentication, user and project permissions, stronger observability, model capacity planning, and a clearer admin dashboard for feature flags and runtime status.

---

## 9. One-Page Presenter Cue Card

### Opening line

GOAT AI is not just a chatbot page. It is a school-deployable AI assistant system with product identity, local runtime control, file workflows, structured outputs, and deployment proof.

### Main flow

1. Show product shell first, not terminal.
2. Open Appearance: Classic, URochester, THU.
3. Explain token-driven theming and `theme_style` persona.
4. Show model selector and local school runtime story.
5. Run streaming chat prompt.
6. Upload a file and ask for summary/key evidence.
7. Generate a simple chart.
8. Explain Workbench/search fallback.
9. Run health, ready, runtime-target, and post-deploy check.
10. Close with product layer + engineering layer.

### Best short phrases

- "This is product infrastructure, not just decoration."
- "The model is only one layer of the system."
- "The school deployment is environment-driven, not source-code-forked."
- "Streaming improves perceived responsiveness and gives the UI typed events."
- "File-grounded work changes the assistant from general chat to a workflow tool."
- "Search should fail honestly, not invent citations."
- "The page opening is not enough; the deployment needs health proof."

### Must-not-overclaim lines

- Do not say it is fully campus-production-ready.
- Say: "controlled school demo deployment."
- Do not say Workbench is an unlimited autonomous agent.
- Say: "bounded research assistance."
- Do not say local runtime solves all privacy concerns.
- Say: "school-controlled environment for supported workloads."

### Emergency close

If time gets cut, close with this:

GOAT AI combines the visible product layer - theme, branding, chat, files, and charts - with the engineering layer - local runtime, typed streaming events, search fallback, and deployment checks. That is the main value of the project: it is not only a model interface, but a deployable AI assistant system.
