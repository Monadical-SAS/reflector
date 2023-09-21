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
};

export function TopicList({ topics, useActiveTopic }: TopicListProps) {
  const [activeTopic, setActiveTopic] = useActiveTopic;
  const [autoscrollEnabled, setAutoscrollEnabled] = useState<boolean>(true);

  useEffect(() => {
    if (autoscrollEnabled) scrollToBottom();
    console.log(topics);
  }, [topics.length]);

  const scrollToBottom = () => {
    const topicsDiv = document.getElementById("topics-div");

    if (!topicsDiv)
      console.error("Could not find topics div to scroll to bottom");
    else topicsDiv.scrollTop = topicsDiv.scrollHeight;
  };

  const handleScroll = (e) => {
    const bottom =
      e.target.scrollHeight - e.target.scrollTop === e.target.clientHeight;
    if (!bottom && autoscrollEnabled) {
      setAutoscrollEnabled(false);
    } else if (bottom && !autoscrollEnabled) {
      setAutoscrollEnabled(true);
    }
  };

  return (
    <section className="relative w-full h-full bg-blue-400/20 rounded-lg md:rounded-xl px-2 md:px-4 flex flex-col justify-center align-center">
      {topics.length > 0 ? (
        <>
          <ScrollToBottom
            visible={!autoscrollEnabled}
            handleScrollBottom={scrollToBottom}
          />

          <div
            id="topics-div"
            className="overflow-y-auto py-2 h-full"
            onScroll={handleScroll}
          >
            {topics.map((topic, index) => (
              <button
                key={index}
                className="rounded-none border-solid border-0 border-b-blue-300 border-b last:border-none p-2 hover:bg-blue-400/20 focus-visible:bg-blue-400/20 text-left block w-full"
                onClick={() =>
                  setActiveTopic(activeTopic?.id == topic.id ? null : topic)
                }
              >
                <div className="w-full flex justify-between items-center rounded-lg md:rounded-xl text-lg md:text-xl font-bold leading-tight">
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
        <div className="text-center text-gray-500 p-4">
          Discussion topics will appear here after you start recording. It may
          take up to 5 minutes of conversation for the first topic to appear.
        </div>
      )}
    </section>
  );
}
