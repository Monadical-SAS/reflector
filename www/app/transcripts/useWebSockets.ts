import { useEffect, useState } from "react";
import { Topic, FinalSummary, Status } from "./webSocketTypes";
import { useError } from "../(errors)/errorContext";

type UseWebSockets = {
  transcriptText: string;
  topics: Topic[];
  finalSummary: FinalSummary;
  status: Status;
};

export const useWebSockets = (transcriptId: string | null): UseWebSockets => {
  const [transcriptText, setTranscriptText] = useState<string>("");
  const [topics, setTopics] = useState<Topic[]>([]);
  const [finalSummary, setFinalSummary] = useState<FinalSummary>({
    summary: "",
  });
  const [status, setStatus] = useState<Status>({ value: "disconnected" });
  const { setError } = useError();

  useEffect(() => {
    document.onkeyup = (e) => {
      if (e.key === "a" && process.env.NEXT_PUBLIC_ENV === "development") {
        setTranscriptText("Lorem Ipsum");
        setTopics([
          {
            id: "1",
            timestamp: 10,
            summary: "This is test topic 1",
            title: "Topic 1: Introduction to Quantum Mechanics",
            transcript:
              "A brief overview of quantum mechanics and its principles.",
          },
          {
            id: "2",
            timestamp: 20,
            summary: "This is test topic 2",
            title: "Topic 2: Machine Learning Algorithms",
            transcript:
              "Understanding the different types of machine learning algorithms.",
          },
          {
            id: "3",
            timestamp: 30,
            summary: "This is test topic 3",
            title: "Topic 3: Mental Health Awareness",
            transcript: "Ways to improve mental health and reduce stigma.",
          },
          {
            id: "4",
            timestamp: 40,
            summary: "This is test topic 4",
            title: "Topic 4: Basics of Productivity",
            transcript: "Tips and tricks to increase daily productivity.",
          },
          {
            id: "5",
            timestamp: 50,
            summary: "This is test topic 5",
            title: "Topic 5: Future of Aviation",
            transcript:
              "Exploring the advancements and possibilities in aviation.",
          },
        ]);

        setFinalSummary({ summary: "This is the final summary" });
      }
    };

    if (!transcriptId) return;

    const url = `${process.env.NEXT_PUBLIC_WEBSOCKET_URL}/v1/transcripts/${transcriptId}/events`;
    const ws = new WebSocket(url);

    ws.onopen = () => {
      console.debug("WebSocket connection opened");
    };

    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);

      try {
        switch (message.event) {
          case "TRANSCRIPT":
            if (message.data.text) {
              setTranscriptText((message.data.text ?? "").trim());
              console.debug("TRANSCRIPT event:", message.data);
            }
            break;

          case "TOPIC":
            setTopics((prevTopics) => [...prevTopics, message.data]);
            console.debug("TOPIC event:", message.data);
            break;

          case "FINAL_LONG_SUMMARY":
            if (message.data) {
              message.data = { summary: message.data.long_summary };
              setFinalSummary(message.data);
              console.debug("FINAL_LONG_SUMMARY event:", message.data);
            }
            break;

          case "FINAL_SUMMARY":
            if (message.data) {
              setFinalSummary(message.data);
              console.debug("FINAL_SUMMARY event:", message.data);
            }
            break;

          case "FINAL_SHORT_SUMMARY":
            console.debug("FINAL_SHORT_SUMMARY event:", message.data);
            break;

          case "FINAL_TITLE":
            console.debug("FINAL_TITLE event:", message.data);
            break;

          case "STATUS":
            setStatus(message.data);
            break;

          default:
            setError(
              new Error(`Received unknown WebSocket event: ${message.event}`),
            );
        }
      } catch (error) {
        setError(error);
      }
    };

    ws.onerror = (error) => {
      console.error("WebSocket error:", error);
      setError(new Error("A WebSocket error occurred."));
    };

    ws.onclose = (event) => {
      console.debug("WebSocket connection closed");
      if (event.code !== 1000) {
        setError(
          new Error(`WebSocket closed unexpectedly with code: ${event.code}`),
        );
      }
    };

    return () => {
      ws.close();
    };
  }, [transcriptId]);

  return { transcriptText, topics, finalSummary, status };
};
