# GOAT AI: Technical Requirement Document & Development Plan

## 1. Project Vision
**GOAT AI** serves as a high-performance "Strategic Intelligence Dashboard" engineered specifically for business executives and analysts at the Simon Business School. The platform's core value lies in providing unparalleled, AI-driven strategic insights securely and at blazing speeds by leveraging local, dedicated A100 GPU resources. By integrating advanced data analysis tools with a robust conversational AI interface, GOAT AI empowers end-users to make data-backed, high-impact business decisions rapidly.

## 2. Technical Stack

### 2.1 Frontend Architecture
*   **Framework:** React 18 powered by Vite for rapid HMR and optimized builds.
*   **Language:** TypeScript (configured with `strict: true` and a rigorous **Zero `any` Policy** for maximum type safety and maintainability).
*   **Styling & UI:** Tailwind CSS for utility-first styling, integrated with Shadcn/UI for accessible, highly customizable component blocks, and Lucide Icons for clean, consistent iconography.
*   **Animations & Visual "Juice":** Framer Motion for premium micro-animations and transition effects, plus Confetti particles for delightful user interactions and celebratory feedback.

### 2.2 Backend & Infrastructure Integration
*   **API Layer:** FastAPI (Python) for asynchronous, high-throughput REST and WebSocket connections.
*   **LLM Engine:** Ollama running locally.
*   **Hardware:** Local A100 GPU resources specifically dedicated to delivering ultra-low latency inference and intensive data analysis without external data exposure.

## 3. Functional Requirements

### 3.1 AI Chat Interface
*   **Real-time Streaming:** Seamless character-by-character token rendering via WebSocket or SSE to simulate real-time thought processing.
*   **Rich Text Rendering:** Comprehensive Markdown support within the chat, including cleanly rendered tables, lists, and inline formatting.
*   **Code & Formula Highlighting:** Syntax highlighting for generated code snippets (Python, SQL) and business formulas.

### 3.2 Business Data Engine
*   **Data Ingestion:** Secure, drag-and-drop CSV and Excel file uploads.
*   **Automated Insights:** Instant parsing and automated statistical summaries (mean, median, variance, trends) generated immediately upon successful upload.

### 3.3 GPU Monitor Widget
*   **Real-time Telemetry:** A distinct visual component situated in the interface to display live GPU inference statistics.
*   **Metrics Tracked:** Active memory usage, inference latency (ms), and generation speed (tokens/sec).

## 4. UI/UX Guidelines

### 4.1 Theme & Typography
*   **Primary Brand Color (Simon Blue):** `#002855` - Used for primary navigation, critical headers, and primary active states to convey trust and professionalism.
*   **Accent Color (Dandelion Yellow):** `#FFCD00` - Used strategically for call-to-actions, primary buttons, and highlighting critical data insights.
*   **Aesthetics:** Modern, clean, and data-forward. The design must feel professional yet engaging, utilizing subtle glassmorphism and smooth Framer Motion transitions to feel highly responsive and polished.

### 4.2 Layout Strategy
*   **Structure:** Responsive sidebar navigation combined with a massive, multi-tab workspace in the central viewing area.
*   **Data Density:** Balanced data presentation, ensuring executives can quickly parse high-level metrics while analysts can dig into dense tables.

## 5. Component Architecture

To maintain a scalable and manageable codebase, the frontend will be atomized into the following core React components:

*   **`ChatPanel`**: The primary conversational interface handling message history, streaming inputs, and Markdown parsing.
*   **`FileAnalyzer`**: A dropzone and processing queue component for handling CSV/Excel files and displaying the automated data summaries.
*   **`ModelSelector`**: A dropdown/modal component allowing users to switch between different locally hosted LLM models optimized for distinct tasks (e.g., Code Generation vs. Business Strategy).
*   **`MetricsCard`**: Reusable dashboard cards for displaying KPIs (used for both the Business Data Engine summaries and the GPU Monitor Widget).
*   **`GPUMonitor`**: The specific implementation of `MetricsCard` that listens to backend telemetry for active hardware stats.
*   **`SidebarNav`**: The primary navigation component housing the "Simon Blue" branding, navigation links, and workspace routing.

## 6. Development Roadmap

### Phase 1: Minimum Viable Product (MVP) Foundation
*   Scaffold the React/Vite/TypeScript application with absolute strict typing.
*   Establish the Shadcn/UI integration along with the "Simon Blue" and "Dandelion Yellow" Tailwind theme configuration.
*   Build the core `ChatPanel` with static mocked responses and Markdown rendering capabilities.
*   Implement the `SidebarNav` and basic application layout.

### Phase 2: AI & Hardware Integration
*   Connect the `ChatPanel` to the FastAPI/Ollama backend to enable live streaming responses.
*   Build and integrate the `GPUMonitor` widget to display live A100 telemetry.
*   Refine chat scrolling, state management, and code highlighting details.

### Phase 3: Business Data Engine
*   Implement the `FileAnalyzer` with secure file uploading.
*   Develop the backend endpoints for CSV/Excel parsing.
*   Create the automated data summary view utilizing `MetricsCard` components.

### Phase 4: Polish & "Juice" (Full-Scale BI Tool)
*   Audit the codebase to ensure 100% adherence to the Zero `any` policy.
*   Integrate Framer Motion for smooth tab switching, modal appearances, and list reordering.
*   Add dynamic Confetti instances for successfully loaded massive datasets or completed complex modeling tasks.
*   Finalize multi-tab workspace functionalities for analyzing multiple datasets/conversations simultaneously.

## 7. Deployment Strategy & Environment Synchronization

To ensure flawless operation across disparate operating systems and strictly adhere to the university's network topology, the following deployment strategy governs the GOAT AI platform.

### 7.1 Environment Drift Mitigation
Deploying from a local environment (Windows/macOS) to the remote **Ubuntu A100 Node** introduces critical environment drift risks:
*   **Case Sensitivity:** Linux environments are strictly case-sensitive. All imports and file paths must rigorously match exact casing to prevent catastrophic 404s and build failures on the remote node.
*   **Dependency Isolation:** Never transfer the `node_modules` directory between environments. It contains OS-specific binaries (like esbuild or SWC) that will fail on Ubuntu. Ensure `node_modules` remains strictly within `.gitignore`.

### 7.2 Git-Based Workflow (The Source of Truth)
A centralized Git pipeline replaces primitive file-copying methods, acting as the absolute source of truth:
1.  **Local IDE:** Develop locally -> `git commit` to finalize features -> `git push` to the designated private GitHub/GitLab repository.
2.  **Remote JupyterLab:** Open the terminal -> `git pull` -> execute `npm install` (to fetch Ubuntu-specific binaries) -> execute `npm run build` to generate the production bundle.
*Note: All dependency updates must be managed strictly via `package-lock.json` lockfiles to guarantee absolute consistency across nodes.*

### 7.3 Path Routing Configuration
The university's Nginx infrastructure routes external requests through a specific subdirectory. To prevent static asset 404 errors, the **Vite Base Path** must be explicitly configured.
*   The `vite.config.ts` file must enforce `base: '/mingzhi/'`. This ensures all injected assets (JS/CSS chunks) are correctly prefixed with `/mingzhi/` in the production `index.html`.

### 7.4 Remote Execution Command
Once compiled (`npm run build`), the static assets within the `dist/` directory must be served exclusively on port **62606**:
*   Execute: `npx serve -s dist -p 62606`
*   *(Alternatively, this can be served via the production Python backend or proxy, provided it strictly binds to port 62606).*

### 7.5 Troubleshooting "It Works on My Machine"
When facing deployment discrepancies, rigorously verify this checklist:
1.  **Path Mismatches:** Audit exact casing of all component imports (e.g., `src/components/...`).
2.  **Environment Variables:** Check for missing or mismatched `.env.production` files on the remote node.
3.  **GPU Driver Initialization:** Ensure the A100 CUDA driver logic within the Python backend is properly engaging without initialization timeouts or memory segmentation faults.
