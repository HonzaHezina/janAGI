# Action Draft protocol (LLM → approval → OpenClaw)

This is the **core safety + robustness pattern** for janAGI when you want an LLM to trigger web/UI actions.

Why you want it:
- prevents “silent” UI automation (you always approve)
- avoids fragile direct tool-calls
- creates a clean audit trail (draft → approval → execution → verification)

---

## 1) Output format the LLM must produce

When the assistant decides it needs OpenClaw, it outputs:

1) a short Czech explanation **what** it wants to do and **why**
2) a machine-readable payload prefixed by `[ACTION_DRAFT]`

Example:

```text
[ACTION_DRAFT] {"kind":"web_read","input":"Go to novinky.cz and identify the latest article on the homepage…","policy":{"allow":["novinky.cz"],"deny":["delete","rotate_credentials"]}}
```

---

## 2) Telegram-safe payload wrapper (highly recommended)

Telegram formatting often breaks JSON. The safest pattern is to embed payload between markers:

```text
🤖 Jackie navrhuje akci přes OpenClaw:

<short human explanation>

---PAYLOAD_JSON---
{ ...valid JSON... }
---END_PAYLOAD_JSON---

✅ Schválit / ❌ Zamítnout
```

---

## 3) n8n implementation (minimal)

### Workflow A — Draft Generation (Inside Handlers)

**Context:** The Router (`WF_42`) has already identified the intent (e.g. `TASK`, `WEB_SEARCH`) and routed to a specific handler (e.g., `WF_44`, `WF_48`).

1.  **Handler Execution:** The specific agent (e.g., Web Researcher) determines an action is needed.
2.  **Output:** It outputs `[ACTION_DRAFT]` + JSON payload.
3.  **Code Node:** Parses draft & normalizes JSON.
4.  **Approval Request:** Sends Telegram message with buttons.

### Workflow B — Execute on Approve
1) Telegram callback query trigger (Approve)
2) Extract payload JSON from the message (between markers)
3) HTTP Request → OpenClaw `/v1/responses`
4) Store response + evidence (DB/event log)
5) Send Telegram “done” + summary

---

## 4) Copy‑paste Code node: extract payload from Telegram message

Use this in an n8n **Code** node (JavaScript):

```js
const text =
  ($json.callback_query?.message?.text ||
   $json.message?.text ||
   $json.text ||
   '').toString();

const A = '---PAYLOAD_JSON---';
const B = '---END_PAYLOAD_JSON---';

let raw = text;
if (text.includes(A) && text.includes(B)) {
  raw = text.split(A)[1].split(B)[0].trim();
} else {
  // fallback: try [ACTION_DRAFT] prefix
  raw = raw.replace(/^\[ACTION_DRAFT\]\s*/,'').trim();
}

let payload = null;
try { payload = JSON.parse(raw); }
catch (e) { payload = { kind: 'text', input: raw }; }

return [{ json: { payload, payload_raw: raw } }];
```

---

## 5) Calling OpenClaw: do NOT mix protocols

### ✅ `/v1/responses` expects:
```json
{"model":"openclaw:main","user":"...","input":"..."}
```

### ✅ `/tools/invoke` expects:
```json
{"tool":"...","action":"json","args":{...},"sessionKey":"...","dryRun":false}
```

If you send a tool-invoke body to `/v1/responses`, you’ll get errors or meaningless output.

---

## 6) Recommended n8n HTTP Request body pattern

Use `JSON.stringify(...)` as raw body expression:

```js
={{JSON.stringify({
  model: "openclaw:main",
  user: "n8n:<stable>",
  input: $json.payload?.input || JSON.stringify($json.payload)
})}}
```
