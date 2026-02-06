// n8n Code Node: Extract Hidden Payload from Telegram Message
// Use this when you have embedded a JSON payload between markers in a human-readable message.
// Useful for [ACTION_DRAFT] -> Approval flow.

const text = ($json.callback_query?.message?.text || $json.message?.text || $json.text || '').toString();

const MARKER_START = '---PAYLOAD_JSON---';
const MARKER_END = '---END_PAYLOAD_JSON---';

let rawPayload = null;
let payloadJson = {};
let extractionMethod = 'none';

if (text.includes(MARKER_START) && text.includes(MARKER_END)) {
  // Method A: Explicit markers (Robust)
  rawPayload = text.split(MARKER_START)[1].split(MARKER_END)[0].trim();
  extractionMethod = 'markers';
} else if (text.includes('[ACTION_DRAFT]')) {
  // Method B: Legacy Action Draft prefix (Fallback)
  rawPayload = text.replace(/^\[ACTION_DRAFT\]\s*/, '').trim();
  extractionMethod = 'legacy_prefix';
} else {
  // Method C: Try to find the first JSON-like block { ... } (Last Resort)
  const firstBrace = text.indexOf('{');
  const lastBrace = text.lastIndexOf('}');
  if (firstBrace >= 0 && lastBrace > firstBrace) {
    rawPayload = text.substring(firstBrace, lastBrace + 1);
    extractionMethod = 'heuristic_json';
  }
}

if (rawPayload) {
  try {
    payloadJson = JSON.parse(rawPayload);
  } catch (e) {
    // If parsing fails, return raw string as 'input'
    payloadJson = { input: rawPayload, error: 'json_parse_failed' };
  }
} else {
  // No payload found, return original text as input
  payloadJson = { input: text.trim(), warning: 'no_payload_found' };
}

// Return standardized structure
return [{
  json: {
    payload: payloadJson,
    payload_raw: rawPayload,
    extraction_method: extractionMethod,
    // Pass verification flags
    is_valid_json: !payloadJson.error,
    has_payload: !!rawPayload
  }
}];
