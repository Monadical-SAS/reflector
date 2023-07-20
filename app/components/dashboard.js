import { Mulberry32 } from "../utils.js";
import React, { useState, useEffect } from "react";
import AudioVisualizer from "./audioVisualizer.js";

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

  return (
    <>
      <div className="w-3/4 py-4">
        <div className="text-center py-6">
          <h1 className="text-4xl font-bold text-blue-500">Reflector</h1>
          <p className="text-gray-500">Capture The Signal, Not The Noise</p>
        </div>
        <div className="flex justify-between border-b-2">
          <div className="w-1/4">Timestamp</div>
          <div className="w-1/4">Topic</div>
          <div className="w-1/4"></div>
        </div>

        {topics.map((item, index) => (
          <div key={index} className="border-b-2 py-2">
            <div
              className="flex justify-between cursor-pointer"
              onClick={() => setOpenIndex(openIndex === index ? null : index)}
            >
              <div className="w-1/4">{item.timestamp}</div>
              <div className="w-1/4">
                {item.title}{" "}
                <span
                  className={`inline-block transform transition-transform duration-200 ${
                    openIndex === index ? "rotate-90" : ""
                  }`}
                >
                  {">"}
                </span>
              </div>
              <div className="w-1/4 flex flex-row space-x-0.5">
              </div>
            </div>
            {openIndex === index && (
              <div className="mt-2 p-2 bg-white">{item.transcript}</div>
            )}
          </div>
        ))}

        <div className="border-b-2 py-2">
          <div className="flex justify-between">
            <div className="w-1/4">Live</div>
            <div className="w-1/4">Transcript</div>
            <div className="w-1/4 flex flex-row space-x-0.5">
            </div>
          </div>
          <div className="mt-2 p-2 bg-white temp-transcription">
            {transcriptionText}
          </div>
        </div>
        <AudioVisualizer isRecording={isRecording} />

        <button
          className="mx-auto mt-6 mb-9"
          onClick={() => onRecord(!isRecording)}
          data-color={isRecording ? "red" : "blue"}
        >
          {isRecording ? "STOP" : "RESUME"}
        </button>

        {finalSummary && (
          <div>
            <h2>Final Summary</h2>
            <p>Duration: {finalSummary.duration}</p>
            <p>{finalSummary.summary}</p>
          </div>
        )}

        <footer className="w-full bg-gray-800 text-center py-4 mt-4 text-white">
          Reflector © 2023 Monadical
        </footer>
      </div>
    </>
  );
}
