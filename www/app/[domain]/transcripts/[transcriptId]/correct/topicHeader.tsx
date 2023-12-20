import { faArrowLeft, faArrowRight } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import useTopics from "../../useTopics";
import { Dispatch, SetStateAction, useEffect } from "react";
import { GetTranscriptTopic } from "../../../../api";

type TopicHeader = {
  stateCurrentTopic: [
    GetTranscriptTopic | undefined,
    Dispatch<SetStateAction<GetTranscriptTopic | undefined>>,
  ];
  transcriptId: string;
  topicWithWordsLoading: boolean;
};

export default function TopicHeader({
  stateCurrentTopic,
  transcriptId,
  topicWithWordsLoading,
}: TopicHeader) {
  const [currentTopic, setCurrentTopic] = stateCurrentTopic;
  const topics = useTopics(transcriptId);

  useEffect(() => {
    if (!topics.loading && !currentTopic) {
      const sessionTopic = window.localStorage.getItem(
        transcriptId + "correct",
      );
      console.log(sessionTopic, window.localStorage);
      if (sessionTopic && topics?.topics?.find((t) => t.id == sessionTopic)) {
        setCurrentTopic(topics?.topics?.find((t) => t.id == sessionTopic));
        console.log("he", sessionTopic, !!sessionTopic);
      } else {
        setCurrentTopic(topics?.topics?.at(0));
        console.log("hi");
      }
    }
  }, [topics.loading]);
  // console.log(currentTopic)

  const number = topics.topics?.findIndex(
    (topic) => topic.id == currentTopic?.id,
  );
  const canGoPrevious = typeof number == "number" && number > 0;
  const total = topics.topics?.length;
  const canGoNext = total && typeof number == "number" && number + 1 < total;

  const onPrev = () => {
    if (topicWithWordsLoading) return;
    canGoPrevious && setCurrentTopic(topics.topics?.at(number - 1));
  };
  const onNext = () => {
    if (topicWithWordsLoading) return;
    canGoNext && setCurrentTopic(topics.topics?.at(number + 1));
  };

  useEffect(() => {
    console.log(currentTopic?.id);

    currentTopic?.id &&
      window.localStorage.setItem(transcriptId + "correct", currentTopic?.id);
  }, [currentTopic?.id]);

  const keyHandler = (e) => {
    if (e.key == "ArrowLeft") {
      onPrev();
    } else if (e.key == "ArrowRight") {
      onNext();
    }
  };
  useEffect(() => {
    document.addEventListener("keyup", keyHandler);
    return () => {
      document.removeEventListener("keyup", keyHandler);
    };
  });

  if (topics.topics && currentTopic && typeof number == "number") {
    return (
      <div className="flex flex-row">
        <button
          className={`w-10 h-10 rounded-full p-2 border border-gray-300 disabled:bg-white ${
            canGoPrevious ? "text-gray-500" : "text-gray-300"
          }`}
          onClick={onPrev}
          disabled={!canGoPrevious}
        >
          <FontAwesomeIcon icon={faArrowLeft} />
        </button>
        <h1 className="flex-grow">
          {currentTopic.title}{" "}
          <span>
            {number + 1}/{total}
          </span>
        </h1>
        <button
          className={`w-10 h-10 rounded-full p-2 border border-gray-300 disabled:bg-white ${
            canGoNext ? "text-gray-500" : "text-gray-300"
          }`}
          onClick={onNext}
          disabled={!canGoNext}
        >
          <FontAwesomeIcon icon={faArrowRight} />
        </button>
      </div>
    );
  }
  return null;
}
