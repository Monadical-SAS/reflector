import { useEffect, useState } from "react";
import { Topic, FinalSummary, Status } from "./webSocketTypes";
import { useError } from "../../(errors)/errorContext";
import type { components } from "../../reflector-api";
type AudioWaveform = components["schemas"]["AudioWaveform"];
type GetTranscriptSegmentTopic =
  components["schemas"]["GetTranscriptSegmentTopic"];
import { useQueryClient } from "@tanstack/react-query";
import { $api, WEBSOCKET_URL } from "../../lib/apiClient";

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
      if (e.key === "a" && process.env.ENV === "development") {
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
      if (e.key === "z" && process.env.ENV === "development") {
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

    const url = `${WEBSOCKET_URL}/v1/transcripts/${transcriptId}/events`;
    let ws = new WebSocket(url);

    ws.onopen = () => {
      console.debug("WebSocket connection opened");
    };

    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);

      try {
        switch (message.event) {
          case "TRANSCRIPT":
            const newText = (message.data.text ?? "").trim();
            const newTranslation = (message.data.translation ?? "").trim();

            if (!newText) break;

            console.debug("TRANSCRIPT event:", newText);
            setTextQueue((prevQueue) => [...prevQueue, newText]);
            setTranslationQueue((prevQueue) => [...prevQueue, newTranslation]);

            setAccumulatedText((prevText) => prevText + " " + newText);
            break;

          case "TOPIC":
            setTopics((prevTopics) => {
              const topic = message.data as Topic;
              const index = prevTopics.findIndex(
                (prevTopic) => prevTopic.id === topic.id,
              );
              if (index >= 0) {
                prevTopics[index] = topic;
                return prevTopics;
              }
              setAccumulatedText((prevText) =>
                prevText.slice(topic.transcript.length),
              );

              return [...prevTopics, topic];
            });
            console.debug("TOPIC event:", message.data);
            // Invalidate topics query to sync with WebSocket data
            queryClient.invalidateQueries({
              queryKey: $api.queryOptions(
                "get",
                "/v1/transcripts/{transcript_id}/topics",
                {
                  params: { path: { transcript_id: transcriptId } },
                },
              ).queryKey,
            });
            break;

          case "FINAL_SHORT_SUMMARY":
            console.debug("FINAL_SHORT_SUMMARY event:", message.data);
            break;

          case "FINAL_LONG_SUMMARY":
            if (message.data) {
              setFinalSummary(message.data);
              // Invalidate transcript query to sync summary
              queryClient.invalidateQueries({
                queryKey: $api.queryOptions(
                  "get",
                  "/v1/transcripts/{transcript_id}",
                  {
                    params: { path: { transcript_id: transcriptId } },
                  },
                ).queryKey,
              });
            }
            break;

          case "FINAL_TITLE":
            console.debug("FINAL_TITLE event:", message.data);
            if (message.data) {
              setTitle(message.data.title);
              // Invalidate transcript query to sync title
              queryClient.invalidateQueries({
                queryKey: $api.queryOptions(
                  "get",
                  "/v1/transcripts/{transcript_id}",
                  {
                    params: { path: { transcript_id: transcriptId } },
                  },
                ).queryKey,
              });
            }
            break;

          case "WAVEFORM":
            console.debug(
              "WAVEFORM event length:",
              message.data.waveform.length,
            );
            if (message.data) {
              setWaveForm(message.data.waveform);
            }
            break;
          case "DURATION":
            console.debug("DURATION event:", message.data);
            if (message.data) {
              setDuration(message.data.duration);
            }
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
            if (message.data.value === "ended") {
              ws.close();
            }
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
          break;
        case 1005: // Closure by client FF
          break;
        case 1001: // Navigate away
          break;
        case 1006: // Closed by client Chrome
          console.warn(
            "WebSocket closed by client, likely duplicated connection in react dev mode",
          );
          break;
        default:
          setError(
            new Error(`WebSocket closed unexpectedly with code: ${event.code}`),
            "Disconnected from the server. Please refresh the page.",
          );
          console.log(
            "Socket is closed. Reconnect will be attempted in 1 second.",
            event.reason,
          );
        // todo handle reconnect with socket.io
      }
    };

    return () => {
      ws.close();
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
