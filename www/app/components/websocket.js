import { useEffect, useState } from "react";

export const useWebSockets = (transcriptId) => {
  const [transcriptText, setTranscriptText] = useState("");
  const [topics, setTopics] = useState([]);
  const [finalSummary, setFinalSummary] = useState("");
  const [status, setStatus] = useState("disconnected");

  useEffect(() => {
    if (!transcriptId) return;

    const url = `${process.env.NEXT_PUBLIC_WEBSOCKET_URL}/v1/transcripts/${transcriptId}/events`;
    const ws = new WebSocket(url);

    ws.onopen = () => {
      console.debug("WebSocket connection opened");
    };

    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);

      switch (message.event) {
        case "TRANSCRIPT":
          if (message.data.text) {
            setTranscriptText(message.data.text.trim());
            console.debug("TRANSCRIPT event:", message.data);
          }
          break;

        case "TOPIC":
          setTopics((prevTopics) => [...prevTopics, message.data]);
          console.debug("TOPIC event:", message.data);
          break;

        case "FINAL_SUMMARY":
          if (message.data.summary) {
            setFinalSummary(message.data.summary.trim());
            console.debug("FINAL_SUMMARY event:", message.data.summary);
          }
          break;

        case "STATUS":
          setStatus(message.data.status);
          break;

        default:
          console.error("Unknown event:", message.event);
      }
    };

    ws.onerror = (error) => {
      console.error("WebSocket error:", error);
    };

    ws.onclose = () => {
      console.debug("WebSocket connection closed");
    };

    return () => {
      ws.close();
    };
  }, [transcriptId]);

  return { transcriptText, topics, finalSummary, status };
};
