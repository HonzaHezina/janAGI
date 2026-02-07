# n8n Workflows: Capabilities & Architecture

This document maps the n8n workflows to the functional capabilities of the janAGI system.
We organize workflows by **Role** (Brain, Hands, Eyes, System) rather than just a flat list.

---

## 🧠 The Brain (Core Assistant)

The entry point for all user interaction is the **Router Architecture**.
Instead of one monolithic workflow, we use a classifier to dispatch intents to specialized sub-flows.

| Workflow File | Role | Description |
|---|---|---|
| **`WF_42_Jackie_Classifier.json`** | **Router / Entry Point** | **Start here.** Receives Telegram Text/Voice. Transcribes voice. Classifies intent (MEETING, TASK, EMAIL, CHAT, WEB, DEV). ACKs immediately, then routes to a sub-workflow. |
| `WF_43_Jackie_Meeting.json` | Handler | Handles calendar events, availability checks. |
| `WF_44_Jackie_Task.json` | Handler | Manages To-Do lists and reminders. |
| `WF_45_Jackie_Email.json` | Handler | Search, read, summarize, and draft emails (Gmail). |
| `WF_46_Jackie_Chat.json` | Handler | General LLM chat with RAG memory (the "default" conversationalist). |
| `WF_47_Jackie_Clarify.json` | Handler | Asks clarifying questions when intent is UNKNOWN or ambiguous. |

*Note: `WF_40_Jackie_Telegram_Assistant` is the V1 monolithic implementation, now being superseded by WF_42.*

---

## 🤲 The Hands (Software Development)

"Spec Kit" is the capability to build software features via spec-driven development.
It consists of a **Chat Interface** (for talking to the user) and a **Build Engine** (for doing the work).

| Workflow File | Role | Description |
|---|---|---|
| **`WF_49_Jackie_SpecKit.json`** | **Interface** | Invoked by WF_42 when intent is `DEV`. Translates user request into a Spec Kit payload and calls the webhook. |
| **`WF_30_SpecKit_Full_Build_Parallel.json`** | **Engine** | The heavy lifter. Triggered by webhook. Runs the full SDLC: `git init`, `specify`, parallel AI coding (Gemini vs Copilot), testing, and PR creation. |
| `spec_kit_workflow.json` | Legacy | Older "Refine Loop" prototype. Use WF_30 for the modern engine. |

---

## 👁️ The Eyes (Web Intelligence)

Capabilities for browsing, searching, and extracting data from the web.

| Workflow File | Role | Description |
|---|---|---|
| **`WF_48_Jackie_Web.json`** | **Interface** | Invoked by WF_42 when intent is `WEB`. Formulates a search/scrape plan and delegates to OpenClaw. |
| `WF_10_Turbo_OpenClaw_Run.json` | Utility | Low-level generic wrapper for calling OpenClaw `/v1/responses`. Used by other workflows. |
| `WF_02_Hunter_Run.json` | Legacy | Old cron-job based crawler. Superseded by on-demand agents (WF_48). |

---

## ⚙️ The System (Ops & Automation)

Tools that Jackie uses to modify the system itself (n8n, databases, etc.).

| Workflow File | Role | Description |
|---|---|---|
| **`WF_20_Builder_Create_Workflow_via_API.json`** | **Automation** | "Text to Workflow". Allows Jackie to creating new n8n workflows by generating JSON and pushing it via the n8n API. |
| `WF_11_Turbo_OpenClaw_UI_Operator.json` | UI Automation | A robust "Plan → Apply → Verify" pattern for OpenClaw to click buttons in the n8n UI (fallback when API is insufficient). |
| `memory_workflows.json` | Infrastructure | API for embedding and retrieving memories from Postgres/pgvector. |

---

## 🗑️ Deprecated / Legacy

Kept for reference or backward compatibility during migration.

- `WF_40_Jackie_Telegram_Assistant.json`: V1 Monolith.
- `main_chat_orchestrator.json`: Prototype.
- `WF_01_Ingest_Message.json`: Prototype ingestion.
- `WF_03_Analyst_Draft...`: Prototype approval flow.
- `WF_04_Executor...`: Replaced by `WF_41`.

---

## Wiring Guide (Post-Import)

After importing `WF_42`, you must manually wire the "Execute Workflow" nodes to the correct sub-flow IDs:

1. Import `WF_42` and all sub-flows (`WF_43`–`WF_49`).
2. Open `WF_42_Jackie_Classifier`.
3. Locate the **Execute Meeting WF** node → Set `Workflow ID` to your imported `WF_43`.
4. Repeat for Task (`WF_44`), Email (`WF_45`), Chat (`WF_46`), Web (`WF_48`), Spec (`WF_49`), Unknown (`WF_47`).
5. Save.

**Test Matrix:**
- Send "Ahoj" → Expect `WF_46` (Chat).
- Send "Naplánuj meeting zítra" → Expect `WF_43` (Meeting).
- Send "Najdi na webu kurz bitcoinu" → Expect `WF_48` (Web).
