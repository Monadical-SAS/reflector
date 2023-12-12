import { faArrowLeft, faArrowRight } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import useTopics from "../../useTopics";
import { Dispatch, SetStateAction, useEffect } from "react";
import { TranscriptTopic } from "../../../../api/models/TranscriptTopic";
import { GetTranscriptTopic } from "../../../../api";

type TopicHeader = {
  stateCurrentTopic: [
    GetTranscriptTopic | undefined,
    Dispatch<SetStateAction<GetTranscriptTopic | undefined>>,
  ];
  transcriptId: string;
};

export default function TopicHeader({
  stateCurrentTopic,
  transcriptId,
}: TopicHeader) {
  const [currentTopic, setCurrentTopic] = stateCurrentTopic;
  const topics = useTopics(transcriptId);

  useEffect(() => {
    if (!topics.loading && !currentTopic) {
      setCurrentTopic(topics?.topics?.at(0));
    }
  }, [topics.loading]);

  if (topics.topics && currentTopic) {
    const number = topics.topics.findIndex(
      (topic) => topic.id == currentTopic.id,
    );
    const canGoPrevious = number > 0;
    const total = topics.topics.length;
    const canGoNext = total && number < total + 1;

    const onPrev = () => setCurrentTopic(topics.topics?.at(number - 1));
    const onNext = () => setCurrentTopic(topics.topics?.at(number + 1));

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
