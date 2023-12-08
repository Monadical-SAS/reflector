import { faArrowLeft, faArrowRight } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import useTopics from "../../useTopics";
import { useEffect } from "react";

export default function TopicHeader({
  currentTopic,
  setCurrentTopic,
  transcriptId,
}) {
  const topics = useTopics(transcriptId);
  useEffect(() => {
    !topics.loading && setCurrentTopic(topics?.topics?.at(0)?.id);
    console.log(currentTopic);
  }, [topics.loading]);

  if (topics.topics) {
    const title = topics.topics.find((topic) => topic.id == currentTopic)
      ?.title;
    const number = topics.topics.findIndex((topic) => topic.id == currentTopic);
    const canGoPrevious = number > 0;
    const total = topics.topics.length;
    const canGoNext = total && number < total + 1;

    const onPrev = () =>
      setCurrentTopic(topics.topics?.at(number - 1)?.id || "");
    const onNext = () =>
      setCurrentTopic(topics.topics?.at(number + 1)?.id || "");

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
          {title}{" "}
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
