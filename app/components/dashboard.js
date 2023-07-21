import { Mulberry32 } from "../utils.js";
import React, { useState, useEffect } from "react";
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faChevronRight, faChevronDown } from '@fortawesome/free-solid-svg-icons'

export function Dashboard({
  isRecording,
  onRecord,
  transcriptionText,
  finalSummary,
  topics,
  stream,
}) {
  const [openIndex, setOpenIndex] = useState(null);
  const [liveTranscript, setLiveTranscript] = useState("");

  topics = [{timestamp: '[00:00]', transcript: 'Abcdef', title: 'This is the title'}];

  return (
    <>
      <div className="w-3/4 py-4">
        <div className="text-center py-6">
          <h1 className="text-2xl font-bold text-blue-500">Meeting Notes</h1>
        </div>
        <div className="flex justify-between border-b-2">
          <div className="w-1/4">Timestamp</div>
          <div className="w-1/4">Topic</div>
          <div className="w-1/4"></div>
        </div>

        {topics.map((item, index) => (
          <div key={index} className="border-b-2 py-2">
            <div
              className="flex justify-between items-center cursor-pointer"
              onClick={() => setOpenIndex(openIndex === index ? null : index)}
            >
              <div className="w-1/4">{item.timestamp}</div>
              <div className="w-1/4 flex justify-between items-center">
                {item.title}
                <FontAwesomeIcon
                  className={`transform transition-transform duration-200`}
                  icon={openIndex === index ? faChevronDown : faChevronRight}
                />
              </div>
              <div className="w-1/4 flex flex-row space-x-0.5"></div>
            </div>
            {openIndex === index && (
              <div className="mt-2 p-2 bg-white rounded">{item.transcript}</div>
            )}
          </div>
        ))}


        <div className="border-b-2 py-2">
          <div className="flex justify-between">
            <div className="w-1/4">Live</div>
            <div className="w-1/4">Transcript</div>
            <div className="w-1/4 flex flex-row space-x-0.5"></div>
          </div>
          <div className="mt-2 p-2 bg-white temp-transcription rounded">
            {transcriptionText}
          </div>
        </div>
      </div>
    </>
  );
}
