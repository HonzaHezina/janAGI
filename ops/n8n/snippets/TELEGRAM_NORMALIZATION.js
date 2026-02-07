// n8n Code node (v2): Normalize Telegram Payload
// Why: Telegram sends 'message' for new chats, but 'callback_query' for button clicks.
//      This unifies them so subsequent nodes (log_event, etc.) always see a chat_id.
// Note: Uses $json (v2 Code node API). For v1 Code nodes, use items[0].json instead.

const body = $json.body || $json; // Webhook body often in 'body'

// Normalize Chat ID
let chatId = undefined;
let user = undefined;
let text = undefined;
let messageId = undefined;

if (body.message) {
  // Standard text message
  chatId = body.message.chat.id;
  user = body.message.from;
  text = body.message.text;
  messageId = body.message.message_id;
} else if (body.callback_query) {
  // Button click (approval/edit)
  chatId = body.callback_query.message.chat.id;
  user = body.callback_query.from;
  text = `[CALLBACK] ${body.callback_query.data}`; // Virtual text
  messageId = body.callback_query.message.message_id;
} else if (body.channel_post) {
  // Channel post
  chatId = body.channel_post.chat.id;
  text = body.channel_post.text;
  messageId = body.channel_post.message_id;
}

// Return unified structure
return [
  {
    json: {
      // Original full payload for raw logging
      raw_payload: body,
      
      // Normalized fields for n8n/DB
      chat_id: chatId ? chatId.toString() : undefined, // Ensure string for rag.*
      user_id: user ? user.id.toString() : undefined,
      user_name: user ? (user.username || user.first_name) : 'unknown',
      text: text || '',
      message_id: messageId,
      
      // Defaults/Metadata
      channel: 'telegram',
      timestamp: new Date().toISOString()
    }
  }
];
