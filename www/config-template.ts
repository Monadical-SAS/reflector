export const localConfig = {
  features: {
    requireLogin: true,
    privacy: true,
    browse: true,
    sendToZulip: true,
    rooms: true,
  },
  api_url: "http://127.0.0.1:1250",
  websocket_url: "ws://127.0.0.1:1250",
  auth_callback_url: "http://localhost:3000/auth-callback",
  zulip_streams: "", // Find the value on zulip
};
