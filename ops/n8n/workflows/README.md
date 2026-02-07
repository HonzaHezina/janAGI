# n8n Workflows Index

This directory contains the workflow templates for janAGI.
For full architectural documentation, see **[ops/docs/WORKFLOWS.md](../../docs/WORKFLOWS.md)**.

## 🗺️ Functional Map

| Functional Capability | Primary Entry Point (Router) | Implementation / Engine |
|---|---|---|
| **Core Assistant (Chat/Voice)** | `WF_42_Jackie_Classifier.json` | `WF_46_Jackie_Chat.json` (conversationalist) |
| **Productivity (Cal/Task/Mail)** | `WF_42_Jackie_Classifier.json` | `WF_43` (Meeting), `WF_44` (Task), `WF_45` (Email) |
| **Software Development** | `WF_49_Jackie_SpecKit.json` | `WF_30_SpecKit_Full_Build_Parallel.json` |
| **Web Research** | `WF_48_Jackie_Web.json` | OpenClaw Turbo (via `/v1/responses`) |
| **System Operations** | *Internal Commands* | `WF_20_Builder_Create_Workflow_via_API.json` |

## 📂 File Naming Convention

- **`WF_4X`**: **Core User Interface.** The main assistant router and its direct sub-handlers. (Active Development)
- **`WF_3X`**: **Heavy Operations.** Long-running complex jobs (e.g., SpecKit Builds).
- **`WF_2X`**: **System Builders.** Workflows that create other workflows.
- **`WF_1X`**: **Core Utilities.** Low-level wrappers (Turbo, UI Operator).
- **`WF_0X`**: **Legacy / Prototypes.** (Deprecated).

## 🚀 Quick Start (Wiring WF_42)

1. Import **`WF_42`** and all **`WF_4X`** subflows.
2. In `WF_42`, update the **Execute Workflow** nodes to point to the IDs of the imported subflows.
3. Enable `WF_42` and the Telegram credential.

*See [WORKFLOWS.md](../../docs/WORKFLOWS.md) for the complete "Wiring Guide".*
