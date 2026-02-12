import { useEffect, useState } from "react";
import { Topic, FinalSummary, Status } from "./webSocketTypes";
import { useError } from "../../(errors)/errorContext";
import type { components, operations } from "../../reflector-api";
type AudioWaveform = components["schemas"]["AudioWaveform"];
type GetTranscriptSegmentTopic =
  components["schemas"]["GetTranscriptSegmentTopic"];
import { useQueryClient } from "@tanstack/react-query";
import { WEBSOCKET_URL } from "../../lib/apiClient";
import {
  invalidateTranscript,
  invalidateTranscriptTopics,
  invalidateTranscriptWaveform,
} from "../../lib/apiHooks";
import { useAuth } from "../../lib/AuthProvider";
import { parseNonEmptyString } from "../../lib/utils";

type TranscriptWsEvent =
  operations["v1_transcript_get_websocket_events"]["responses"][200]["content"]["application/json"];

export type UseWebSockets = {
  transcriptTextLive: string;
  translateText: string;
  accumulatedText: string;
  title: string;
  topics: Topic[];
  finalSummary: FinalSummary;
  status: Status | null;
  waveform: AudioWaveform | null;
  duration: number | null;
};

export const useWebSockets = (transcriptId: string | null): UseWebSockets => {
  const auth = useAuth();
  const [transcriptTextLive, setTranscriptTextLive] = useState<string>("");
  const [translateText, setTranslateText] = useState<string>("");
  const [title, setTitle] = useState<string>("");
  const [textQueue, setTextQueue] = useState<string[]>([]);
  const [translationQueue, setTranslationQueue] = useState<string[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [topics, setTopics] = useState<Topic[]>([]);
  const [waveform, setWaveForm] = useState<AudioWaveform | null>(null);
  const [duration, setDuration] = useState<number | null>(null);
  const [finalSummary, setFinalSummary] = useState<FinalSummary>({
    summary: "",
  });
  const [status, setStatus] = useState<Status | null>(null);
  const { setError } = useError();

  const queryClient = useQueryClient();

  const [accumulatedText, setAccumulatedText] = useState<string>("");

  useEffect(() => {
    if (isProcessing || textQueue.length === 0) {
      return;
    }

    setIsProcessing(true);
    const text = textQueue[0];
    setTranscriptTextLive(text);
    setTranslateText(translationQueue[0]);

    const WPM_READING = 200 + textQueue.length * 10; // words per minute to read
    const wordCount = text.split(/\s+/).length;
    const delay = (wordCount / WPM_READING) * 60 * 1000;
    setTimeout(() => {
      setIsProcessing(false);
      setTextQueue((prevQueue) => prevQueue.slice(1));
      setTranslationQueue((prevQueue) => prevQueue.slice(1));
    }, delay);
  }, [textQueue, isProcessing]);

  useEffect(() => {
    document.onkeyup = (e) => {
      if (e.key === "a" && process.env.NODE_ENV === "development") {
        const segments: GetTranscriptSegmentTopic[] = [
          {
            speaker: 1,
            start: 0,
            text: "This is the transcription of an example title",
          },
          {
            speaker: 2,
            start: 10,
            text: "This is the second speaker",
          },
          {
            speaker: 3,
            start: 90,
            text: "This is the third speaker",
          },
          {
            speaker: 4,
            start: 90,
            text: "This is the fourth speaker",
          },
          {
            speaker: 5,
            start: 123,
            text: "This is the fifth speaker",
          },
          {
            speaker: 6,
            start: 300,
            text: "This is the sixth speaker",
          },
        ];

        setTranscriptTextLive("Lorem Ipsum");
        setStatus({ value: "recording" });
        setTopics([
          {
            id: "1",
            timestamp: 10,
            duration: 10,
            summary: "This is test topic 1",
            title: "Topic 1: Introduction to Quantum Mechanics",
            transcript:
              "A brief overview of quantum mechanics and its principles.",
            segments: [
              {
                speaker: 1,
                start: 0,
                text: "This is the transcription of an example title",
              },
            ],
          },
          {
            id: "2",
            timestamp: 20,
            duration: 10,
            summary: "This is test topic 2",
            title: "Topic 2: Machine Learning Algorithms",
            transcript:
              "Understanding the different types of machine learning algorithms.",
            segments: [
              {
                speaker: 1,
                start: 0,
                text: "This is the transcription of an example title",
              },
              {
                speaker: 2,
                start: 10,
                text: "This is the second speaker",
              },
            ],
          },
          {
            id: "3",
            timestamp: 30,
            duration: 10,
            summary: "This is test topic 3",
            title: "Topic 3: Mental Health Awareness",
            transcript: "Ways to improve mental health and reduce stigma.",
            segments: [
              {
                speaker: 1,
                start: 0,
                text: "This is the transcription of an example title",
              },
              {
                speaker: 2,
                start: 10,
                text: "This is the second speaker",
              },
            ],
          },
          {
            id: "4",
            timestamp: 40,
            duration: 10,
            summary: "This is test topic 4",
            title: "Topic 4: Basics of Productivity",
            transcript: "Tips and tricks to increase daily productivity.",
            segments: [
              {
                speaker: 1,
                start: 0,
                text: "This is the transcription of an example title",
              },
              {
                speaker: 2,
                start: 10,
                text: "This is the second speaker",
              },
            ],
          },
          {
            id: "5",
            timestamp: 50,
            duration: 10,
            summary: "This is test topic 5",
            title: "Topic 5: Future of Aviation",
            transcript:
              "Exploring the advancements and possibilities in aviation.",
            segments: [
              {
                speaker: 1,
                start: 0,
                text: "This is the transcription of an example title",
              },
              {
                speaker: 2,
                start: 10,
                text: "This is the second speaker",
              },
            ],
          },
        ]);

        setFinalSummary({ summary: "This is the final summary" });
      }
      if (e.key === "z" && process.env.NODE_ENV === "development") {
        setTranscriptTextLive(
          "This text is in English, and it is a pretty long sentence to test the limits",
        );
        setAccumulatedText(
          "This text is in English, and it is a pretty long sentence to test the limits. This text is in English, and it is a pretty long sentence to test the limits",
        );
        setStatus({ value: "processing" });
        setTopics([
          {
            id: "1",
            timestamp: 10,
            duration: 10,
            summary: "This is test topic 1",
            title:
              "Topic 1: Introduction to Quantum Mechanics, a brief overview of quantum mechanics and its principles.",
            transcript:
              "A brief overview of quantum mechanics and its principles.",
            segments: [
              {
                speaker: 1,
                start: 0,
                text: "This is the transcription of an example title",
              },
              {
                speaker: 2,
                start: 10,
                text: "This is the second speaker",
              },
            ],
          },
          {
            id: "2",
            timestamp: 20,
            duration: 10,
            summary: "This is test topic 2",
            title:
              "Topic 2: Machine Learning Algorithms, understanding the different types of machine learning algorithms.",
            transcript:
              "Understanding the different types of machine learning algorithms.",
            segments: [
              {
                speaker: 1,
                start: 0,
                text: "This is the transcription of an example title",
              },
              {
                speaker: 2,
                start: 10,
                text: "This is the second speaker",
              },
            ],
          },
          {
            id: "3",
            timestamp: 30,
            duration: 10,
            summary: "This is test topic 3",
            title:
              "Topic 3: Mental Health Awareness, ways to improve mental health and reduce stigma.",
            transcript: "Ways to improve mental health and reduce stigma.",
            segments: [
              {
                speaker: 1,
                start: 0,
                text: "This is the transcription of an example title",
              },
              {
                speaker: 2,
                start: 10,
                text: "This is the second speaker",
              },
            ],
          },
          {
            id: "4",
            timestamp: 40,
            duration: 10,
            summary: "This is test topic 4",
            title:
              "Topic 4: Basics of Productivity, tips and tricks to increase daily productivity.",
            transcript: "Tips and tricks to increase daily productivity.",
            segments: [
              {
                speaker: 1,
                start: 0,
                text: "This is the transcription of an example title",
              },
              {
                speaker: 2,
                start: 10,
                text: "This is the second speaker",
              },
            ],
          },
          {
            id: "5",
            timestamp: 50,
            duration: 10,
            summary: "This is test topic 5",
            title:
              "Topic 5: Future of Aviation, exploring the advancements and possibilities in aviation.",
            transcript:
              "Exploring the advancements and possibilities in aviation.",
            segments: [
              {
                speaker: 1,
                start: 0,
                text: "This is the transcription of an example title",
              },
              {
                speaker: 2,
                start: 10,
                text: "This is the second speaker",
              },
            ],
          },
        ]);

        setFinalSummary({ summary: "This is the final summary" });
      }
    };

    if (!transcriptId) return;
    const tsId = parseNonEmptyString(transcriptId);

    const MAX_RETRIES = 10;
    const url = `${WEBSOCKET_URL}/v1/transcripts/${transcriptId}/events`;
    let ws: WebSocket | null = null;
    let retryCount = 0;
    let retryTimeout: ReturnType<typeof setTimeout> | null = null;
    let intentionalClose = false;

    const connect = () => {
      const subprotocols = auth.accessToken
        ? ["bearer", auth.accessToken]
        : undefined;
      ws = new WebSocket(url, subprotocols);

      ws.onopen = () => {
        console.debug("WebSocket connection opened");
        retryCount = 0;
      };

      ws.onmessage = (event) => {
        const message: TranscriptWsEvent = JSON.parse(event.data);

        try {
          switch (message.event) {
            case "TRANSCRIPT": {
              const newText = (message.data.text ?? "").trim();
              const newTranslation = (message.data.translation ?? "").trim();

              if (!newText) break;

              console.debug("TRANSCRIPT event:", newText);
              setTextQueue((prevQueue) => [...prevQueue, newText]);
              setTranslationQueue((prevQueue) => [
                ...prevQueue,
                newTranslation,
              ]);

              setAccumulatedText((prevText) => prevText + " " + newText);
              break;
            }

            case "TOPIC":
              setTopics((prevTopics) => {
                // WS sends TranscriptTopic (words), frontend Topic uses segments — works at runtime
                const topic = message.data as unknown as Topic;
                const index = prevTopics.findIndex(
                  (prevTopic) => prevTopic.id === topic.id,
                );
                if (index >= 0) {
                  prevTopics[index] = topic;
                  return prevTopics;
                }
                setAccumulatedText((prevText) =>
                  prevText.slice(topic.transcript?.length ?? 0),
                );
                return [...prevTopics, topic];
              });
              console.debug("TOPIC event:", message.data);
              invalidateTranscriptTopics(queryClient, tsId);
              break;

            case "FINAL_SHORT_SUMMARY":
              console.debug("FINAL_SHORT_SUMMARY event:", message.data);
              break;

            case "FINAL_LONG_SUMMARY":
              setFinalSummary({ summary: message.data.long_summary });
              invalidateTranscript(queryClient, tsId);
              break;

            case "FINAL_TITLE":
              console.debug("FINAL_TITLE event:", message.data);
              setTitle(message.data.title);
              invalidateTranscript(queryClient, tsId);
              break;

            case "WAVEFORM":
              console.debug(
                "WAVEFORM event length:",
                message.data.waveform.length,
              );
              setWaveForm({ data: message.data.waveform });
              invalidateTranscriptWaveform(queryClient, tsId);
              break;

            case "DURATION":
              console.debug("DURATION event:", message.data);
              setDuration(message.data.duration);
              break;

            case "STATUS":
              console.log("STATUS event:", message.data);
              if (message.data.value === "error") {
                setError(
                  Error("Websocket error status"),
                  "There was an error processing this meeting.",
                );
              }
              setStatus(message.data);
              invalidateTranscript(queryClient, tsId);
              if (message.data.value === "ended") {
                intentionalClose = true;
                ws?.close();
              }
              break;

            case "ACTION_ITEMS":
              console.debug("ACTION_ITEMS event:", message.data);
              invalidateTranscript(queryClient, tsId);
              break;

            default: {
              const _exhaustive: never = message;
              console.warn(
                `Received unknown WebSocket event: ${(_exhaustive as TranscriptWsEvent).event}`,
              );
            }
          }
        } catch (error) {
          setError(error);
        }
      };

      ws.onerror = (error) => {
        console.error("WebSocket error:", error);
      };

      ws.onclose = (event) => {
        console.debug("WebSocket connection closed, code:", event.code);
        if (intentionalClose) return;

        const normalCodes = [1000, 1001, 1005];
        if (normalCodes.includes(event.code)) return;

        if (retryCount < MAX_RETRIES) {
          const delay = Math.min(1000 * Math.pow(2, retryCount), 30000);
          console.log(
            `WebSocket reconnecting in ${delay}ms (attempt ${retryCount + 1}/${MAX_RETRIES})`,
          );
          if (retryCount === 0) {
            setError(
              new Error("WebSocket connection lost"),
              "Connection lost. Reconnecting...",
            );
          }
          retryCount++;
          retryTimeout = setTimeout(connect, delay);
        } else {
          setError(
            new Error(`WebSocket closed unexpectedly with code: ${event.code}`),
            "Disconnected from the server. Please refresh the page.",
          );
        }
      };
    };

    connect();

    return () => {
      intentionalClose = true;
      if (retryTimeout) clearTimeout(retryTimeout);
      ws?.close();
    };
  }, [transcriptId]);

  return {
    transcriptTextLive,
    translateText,
    accumulatedText,
    topics,
    finalSummary,
    title,
    status,
    waveform,
    duration,
  };
};
