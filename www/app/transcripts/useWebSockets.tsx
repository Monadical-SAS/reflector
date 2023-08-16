import { useEffect, useState } from "react";
import { TopicType, FinalSummaryType, StatusType } from "./webSocketTypes";

type UseWebSocketsReturnType = {
  transcriptText: string;
  topics: TopicType[];
  finalSummary: FinalSummaryType;
  status: StatusType;
};

export const useWebSockets = (
  transcriptId: string | null,
): UseWebSocketsReturnType => {
  const [transcriptText, setTranscriptText] = useState<string>("");
  const [topics, setTopics] = useState<TopicType[]>([]);
  const [finalSummary, setFinalSummary] = useState<FinalSummaryType>({
    summary: "",
  });
  const [status, setStatus] = useState<StatusType>({ value: "disconnected" });

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
          if (message.data) {
            setFinalSummary(message.data);
            console.debug("FINAL_SUMMARY event:", message.data);
          }
          break;

        case "STATUS":
          setStatus(message.data);
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
