import React, { useState, useEffect } from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faChevronRight,
  faChevronDown,
} from "@fortawesome/free-solid-svg-icons";
import { formatTime } from "../lib/time";
import ScrollToBottom from "./scrollToBottom";
import DisconnectedIndicator from "./disconnectedIndicator";
import LiveTrancription from "./liveTranscription";
import FinalSummary from "./finalSummary";
import { Topic, FinalSummary as FinalSummaryType } from "./webSocketTypes";

type DashboardProps = {
  transcriptionText: string;
  finalSummary: FinalSummaryType;
  topics: Topic[];
  disconnected: boolean;
  useActiveTopic: [
    Topic | null,
    React.Dispatch<React.SetStateAction<Topic | null>>,
  ];
};

export function Dashboard({
  transcriptionText,
  finalSummary,
  topics,
  disconnected,
  useActiveTopic,
}: DashboardProps) {
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
    <div className="py-4 grid grid-cols-1 lg:grid-cols-2 gap-2 lg:gap-4 grid-rows-2 lg:grid-rows-1 h-outer-dashboard md:h-outer-dashboard-md lg:h-outer-dashboard-lg">
      {/* Topic Section */}
      <section className="relative w-full h-auto max-h-full bg-blue-400/20 rounded-lg md:rounded-xl px-2 md:px-4 flex flex-col justify-center align-center">
        {topics.length > 0 ? (
          <>
            <ScrollToBottom
              visible={!autoscrollEnabled}
              hasFinalSummary={finalSummary ? true : false}
              handleScrollBottom={scrollToBottom}
            />

            <div
              id="topics-div"
              className="overflow-y-auto h-auto max-h-full"
              onScroll={handleScroll}
            >
              {topics.map((item, index) => (
                <div
                  key={index}
                  className="border-b-2 last:border-none px-2 md:px-4 py-2 hover:bg-blue-400/20"
                  role="button"
                  onClick={() =>
                    setActiveTopic(activeTopic?.id == item.id ? null : item)
                  }
                >
                  <div className="flex justify-between items-center rounded-lg md:rounded-xl text-l md:text-xl font-bold">
                    <p>
                      <span className="font-light text-slate-500 pr-1">
                        [{formatTime(item.timestamp)}]
                      </span>
                      &nbsp;
                      <span className="pr-1">{item.title}</span>
                    </p>
                    <FontAwesomeIcon
                      className="transform transition-transform duration-200"
                      icon={
                        activeTopic?.id == item.id
                          ? faChevronDown
                          : faChevronRight
                      }
                    />
                  </div>
                  {activeTopic?.id == item.id && (
                    <div className="p-2 mt-2 -mb-2 h-fit">
                      {item.transcript}
                    </div>
                  )}
                </div>
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

      <section className="relative w-full h-auto max-h-full bg-blue-400/20 rounded-lg md:rounded-xl px-2 md:px-4 flex flex-col justify-center align-center">
        {finalSummary.summary ? (
          <FinalSummary text={finalSummary.summary} />
        ) : (
          <LiveTrancription text={transcriptionText} />
        )}
      </section>

      {disconnected && <DisconnectedIndicator />}
    </div>
  );
}
