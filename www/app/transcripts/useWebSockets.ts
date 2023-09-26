import { useEffect, useState } from "react";
import { Topic, FinalSummary, Status } from "./webSocketTypes";
import { useError } from "../(errors)/errorContext";
import { useRouter } from "next/navigation";

type UseWebSockets = {
  transcriptText: string;
  topics: Topic[];
  finalSummary: FinalSummary;
  status: Status;
};

export const useWebSockets = (transcriptId: string | null): UseWebSockets => {
  const [transcriptText, setTranscriptText] = useState<string>("");
  const [textQueue, setTextQueue] = useState<string[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [topics, setTopics] = useState<Topic[]>([]);
  const [finalSummary, setFinalSummary] = useState<FinalSummary>({
    summary: "",
  });
  const [status, setStatus] = useState<Status>({ value: "disconnected" });
  const { setError } = useError();
  const router = useRouter();

  useEffect(() => {
    if (isProcessing || textQueue.length === 0) {
      return;
    }

    setIsProcessing(true);
    const text = textQueue[0];
    setTranscriptText(text);

    const WPM_READING = 200; // words per minute to read
    const wordCount = text.split(/\s+/).length;
    const delay = (wordCount / WPM_READING) * 60 * 1000;
    setTimeout(() => {
      setIsProcessing(false);
      setTextQueue((prevQueue) => prevQueue.slice(1));
    }, delay);
  }, [textQueue, isProcessing]);

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
      if (e.key === "z" && process.env.NEXT_PUBLIC_ENV === "development") {
        setTranscriptText(
          "This text is in English, and it is a pretty long sentence to test the limits",
        );
        setTopics([
          {
            id: "1",
            timestamp: 10,
            summary: "This is test topic 1",
            title:
              "Topic 1: Introduction to Quantum Mechanics, a brief overview of quantum mechanics and its principles.",
            transcript:
              "A brief overview of quantum mechanics and its principles.",
          },
          {
            id: "2",
            timestamp: 20,
            summary: "This is test topic 2",
            title:
              "Topic 2: Machine Learning Algorithms, understanding the different types of machine learning algorithms.",
            transcript:
              "Understanding the different types of machine learning algorithms.",
          },
          {
            id: "3",
            timestamp: 30,
            summary: "This is test topic 3",
            title:
              "Topic 3: Mental Health Awareness, ways to improve mental health and reduce stigma.",
            transcript: "Ways to improve mental health and reduce stigma.",
          },
          {
            id: "4",
            timestamp: 40,
            summary: "This is test topic 4",
            title:
              "Topic 4: Basics of Productivity, tips and tricks to increase daily productivity.",
            transcript: "Tips and tricks to increase daily productivity.",
          },
          {
            id: "5",
            timestamp: 50,
            summary: "This is test topic 5",
            title:
              "Topic 5: Future of Aviation, exploring the advancements and possibilities in aviation.",
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
            const newText = (message.data.text ?? "").trim();

            if (!newText) break;

            console.debug("TRANSCRIPT event:", newText);
            setTextQueue((prevQueue) => [...prevQueue, newText]);
            break;

          case "TOPIC":
            setTopics((prevTopics) => [...prevTopics, message.data]);
            console.debug("TOPIC event:", message.data);
            break;

          case "FINAL_SHORT_SUMMARY":
            console.debug("FINAL_SHORT_SUMMARY event:", message.data);
            break;

          case "FINAL_LONG_SUMMARY":
            if (message.data) {
              setFinalSummary(message.data);
              const newUrl = "/transcripts/" + transcriptId;
              router.push(newUrl);
              console.debug(
                "FINAL_LONG_SUMMARY event:",
                message.data,
                "newUrl",
                newUrl,
              );
            }
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
      switch (event.code) {
        case 1000: // Normal Closure:
        case 1001: // Going Away:
        case 1005:
          break;
        default:
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
