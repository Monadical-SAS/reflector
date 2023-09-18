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

  const faketopic = {
    id: "641fbc68-dc2e-4c9d-aafd-89bdbf8cfc26",
    summary:
      "Explore the history of hypnotica music, a genre that has been deeply influential on modern music. From its origins in the 60s to its current status, this music has a unique and hypnotic quality that can be felt in the gut. Dive into the canon of modern hypnotica and discover its impact on music today.",
    timestamp: 0,
    title: "The Origins and Influence of Hypnotica Music",
    transcript:
      " vertically oriented music ultimately hypnotic So, that's what we're talking about. Uh, when does it start? I mean, technically, I think... It's always been here but Hypnotica, much like Exotica, which is also sort of a fraught genre. a sort of a western interpretive genre, a fetishizing genre. I would say, uh, it starts in the 60s when all these wh- weird things started, you know, and I started fucking around and... You can go into Woodstock or whatever, that's usually when these things start. Anything that ends with a at the end of a word usually started in By some dirty hippie. Yeah. By some dirty hippie. Yeah. It was like, uh. Okay. So. That's hypnotica, I don't care to explain it to be honest I think everyone can feel it in their gut. We're mostly gonna ex- Explore this kind of the canon of the modern canon of what what I might call hypnotic It's been deeply influential on me and, uh...",
  };
  const faketopics = new Array(10).fill(faketopic);

  return (
    <div className="py-4 grid grid-cols-1 lg:grid-cols-2 gap-2 lg:gap-4 grid-rows-2 lg:grid-rows-1 h-outer-dashboard md:h-outer-dashboard-md lg:h-outer-dashboard-lg">
      {/* Topic Section */}
      <section className="relative w-full h-auto max-h-full bg-blue-400/20 rounded-lg md:rounded-xl px-2 md:px-4 flex flex-col justify-center align-center">
        {faketopics.length > 0 ? (
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
              {faketopics.map((item, index) => (
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
