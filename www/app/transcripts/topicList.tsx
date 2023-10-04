import React, { useState, useEffect } from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faChevronRight,
  faChevronDown,
} from "@fortawesome/free-solid-svg-icons";
import { formatTime } from "../lib/time";
import ScrollToBottom from "./scrollToBottom";
import { Topic } from "./webSocketTypes";

type TopicListProps = {
  topics: Topic[];
  useActiveTopic: [
    Topic | null,
    React.Dispatch<React.SetStateAction<Topic | null>>,
  ];
  autoscroll: boolean;
};

export function TopicList({
  topics,
  useActiveTopic,
  autoscroll,
}: TopicListProps) {
  const [activeTopic, setActiveTopic] = useActiveTopic;
  const [autoscrollEnabled, setAutoscrollEnabled] = useState<boolean>(true);

  useEffect(() => {
    if (autoscroll && autoscrollEnabled) scrollToBottom();
  }, [topics.length]);

  const scrollToBottom = () => {
    const topicsDiv = document.getElementById("topics-div");

    if (topicsDiv) topicsDiv.scrollTop = topicsDiv.scrollHeight;
  };

  // scroll top is not rounded, heights are, so exact match won't work.
  // https://developer.mozilla.org/en-US/docs/Web/API/Element/scrollHeight#determine_if_an_element_has_been_totally_scrolled
  const toggleScroll = (element) => {
    const bottom =
      Math.abs(
        element.scrollHeight - element.clientHeight - element.scrollTop,
      ) < 2 || element.scrollHeight == element.clientHeight;
    if (!bottom && autoscrollEnabled) {
      setAutoscrollEnabled(false);
    } else if (bottom && !autoscrollEnabled) {
      setAutoscrollEnabled(true);
    }
  };
  const handleScroll = (e) => {
    toggleScroll(e.target);
  };

  useEffect(() => {
    if (autoscroll) {
      const topicsDiv = document.getElementById("topics-div");

      topicsDiv && toggleScroll(topicsDiv);
    }
  }, [activeTopic, autoscroll]);

  return (
    <section className="relative w-full h-full bg-blue-400/20 rounded-lg md:rounded-xl p-1 sm:p-2 md:px-4 flex flex-col justify-center align-center">
      {topics.length > 0 ? (
        <>
          <h2 className="ml-2 md:text-lg font-bold mb-2">Topics</h2>

          {autoscroll && (
            <ScrollToBottom
              visible={!autoscrollEnabled}
              handleScrollBottom={scrollToBottom}
            />
          )}

          <div
            id="topics-div"
            className="overflow-y-auto h-full"
            onScroll={handleScroll}
          >
            {topics.map((topic, index) => (
              <button
                key={index}
                className="rounded-none border-solid border-0 border-bluegrey border-b last:border-none last:rounded-b-lg p-2 hover:bg-blue-400/20 focus-visible:bg-blue-400/20 text-left block w-full"
                onClick={() =>
                  setActiveTopic(activeTopic?.id == topic.id ? null : topic)
                }
              >
                <div className="w-full flex justify-between items-center rounded-lg md:rounded-xl xs:text-base sm:text-lg md:text-xl font-bold leading-tight">
                  <p>
                    <span className="font-light font-mono text-slate-500 text-base md:text-lg">
                      [{formatTime(topic.timestamp)}]&nbsp;
                    </span>
                    <span>{topic.title}</span>
                  </p>
                  <FontAwesomeIcon
                    className="transform transition-transform duration-200 ml-2"
                    icon={
                      activeTopic?.id == topic.id
                        ? faChevronDown
                        : faChevronRight
                    }
                  />
                </div>
                {activeTopic?.id == topic.id && (
                  <div className="p-2">{topic.transcript}</div>
                )}
              </button>
            ))}
          </div>
        </>
      ) : (
        <div className="text-center text-gray-500">
          Discussion topics will appear here after you start recording.
          <br />
          It may take up to 5 minutes of conversation for the first topic to
          appear.
        </div>
      )}
    </section>
  );
}
