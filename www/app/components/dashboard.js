import { Mulberry32 } from "../utils.js";
import React, { useState, useEffect } from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faChevronRight,
  faChevronDown,
} from "@fortawesome/free-solid-svg-icons";

export function Dashboard({
  isRecording,
  onRecord,
  transcriptionText,
  finalSummary,
  topics,
  stream,
}) {
  const [openIndex, setOpenIndex] = useState(null);
  const [autoscrollEnabled, setAutoscrollEnabled] = useState(true);

  useEffect(() => {
    if (autoscrollEnabled) scrollToBottom();
  }, [topics.length]);

  const scrollToBottom = () => {
    const topicsDiv = document.getElementById("topics-div");
    topicsDiv.scrollTop = topicsDiv.scrollHeight;
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

  const formatTime = (seconds) => {
    let hours = Math.floor(seconds / 3600);
    let minutes = Math.floor((seconds % 3600) / 60);
    let secs = Math.floor(seconds % 60);

    let timeString = `${hours > 0 ? hours + ":" : ""}${minutes
      .toString()
      .padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;

    return timeString;
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

        <div
          className={`absolute right-5 w-10 h-10 ${
            autoscrollEnabled ? "hidden" : "flex"
          } ${
            finalSummary ? "top-[49%]" : "bottom-1"
          } justify-center items-center text-2xl cursor-pointer opacity-70 hover:opacity-100 transition-opacity duration-200 animate-bounce rounded-xl border-slate-400 bg-[#3c82f638] text-[#3c82f6ed]`}
          onClick={scrollToBottom}
        >
          &#11015;
        </div>
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

        {finalSummary && (
          <div className="min-h-[200px] overflow-y-auto mt-2 p-2 bg-white temp-transcription rounded">
            <h2>Final Summary</h2>
            <p>{finalSummary}</p>
          </div>
        )}
      </div>

      <footer className="h-[7svh] w-full bg-gray-800 text-white text-center py-4 text-2xl">
        &nbsp;{transcriptionText}&nbsp;
      </footer>
    </>
  );
}
