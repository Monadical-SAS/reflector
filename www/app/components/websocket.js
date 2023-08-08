import { useEffect } from "react";

export const useWebSockets = (transcript_id) => {
  useEffect(() => {
    if (!transcript_id) return;

    const url = `${process.env.NEXT_PUBLIC_WEBSOCKET_URL}/v1/transcripts/${transcript_id}/events`;
    const ws = new WebSocket(url);
    console.log("Opening websocket: ", url);

    ws.onopen = () => {
      console.log("WebSocket connection opened");
    };

    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);

      switch (message.event) {
        case "TRANSCRIPT":
          if (!message.data.text) break;
          console.log("TRANSCRIPT event:", message.data.text);
          break;
        case "TOPIC":
          console.log("TOPIC event:", message.data);
          break;
        case "FINAL_SUMMARY":
          console.log("FINAL_SUMMARY event:", message.data.summary);
          break;
        default:
          console.error("Unknown event:", message.event);
      }
    };

    ws.onerror = (error) => {
      console.error("WebSocket error:", error);
    };

    ws.onclose = () => {
      console.log("WebSocket connection closed");
    };

    return () => {
      ws.close();
    };
  }, [transcript_id]);
};
