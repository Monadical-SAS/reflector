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
};

export function Dashboard({
  transcriptionText,
  finalSummary,
  topics,
  disconnected,
}: DashboardProps) {
  const [openIndex, setOpenIndex] = useState<number | null>(null);
  const [autoscrollEnabled, setAutoscrollEnabled] = useState<boolean>(true);

  useEffect(() => {
    if (autoscrollEnabled) scrollToBottom();
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
    <>
      <div className="relative h-[60svh] w-3/4 flex flex-col">
        <div className="text-center pb-1 pt-4">
          <h1 className="text-2xl font-bold text-blue-500">Meeting Notes</h1>
        </div>
        <div className="flex justify-between border-b-2">
          <div className="w-1/4 font-bold">Timestamp</div>
          <div className="w-3/4 font-bold">Topic</div>
        </div>

        <ScrollToBottom
          visible={!autoscrollEnabled}
          hasFinalSummary={finalSummary ? true : false}
          handleScrollBottom={scrollToBottom}
        />

        <div
          id="topics-div"
          className="py-2 overflow-y-auto"
          onScroll={handleScroll}
        >
          {topics.map((item, index) => (
            <div key={index} className="border-b-2 py-2 hover:bg-[#8ec5fc30]">
              <div
                className="flex justify-between items-center cursor-pointer px-4"
                onClick={() => setOpenIndex(openIndex === index ? null : index)}
              >
                <div className="w-1/4">{formatTime(item.timestamp)}</div>
                <div className="w-3/4 flex justify-between items-center">
                  {item.title}
                  <FontAwesomeIcon
                    className={`transform transition-transform duration-200`}
                    icon={openIndex === index ? faChevronDown : faChevronRight}
                  />
                </div>
              </div>
              {openIndex === index && (
                <div className="p-2 mt-2 -mb-2 bg-slate-50 rounded">
                  {item.transcript}
                </div>
              )}
            </div>
          ))}
          {topics.length === 0 && (
            <div className="text-center text-gray-500">No topics yet</div>
          )}
        </div>

        {finalSummary.summary && <FinalSummary text={finalSummary.summary} />}
      </div>

      {disconnected && <DisconnectedIndicator />}

      <LiveTrancription text={transcriptionText} />
    </>
  );
}
