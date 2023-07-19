import { Mulberry32 } from "../utils.js";
import React, { useState, useEffect } from "react";

export function Dashboard(props) {
  const [openIndex, setOpenIndex] = useState(null);
  const [liveTranscript, setLiveTranscript] = useState("");

  const fakeTranscripts = [
    "This is the first transcript. We are discussing the current situation of our company. We are currently leading the market with a significant margin, and our future outlook is also very promising...",
    "Here is the second transcript. We are now moving to our next topic, which is the progress in our ongoing projects. Most of them are on schedule and the quality of work is up to our standard...",
    "This is the third transcript. It's about the financial status of our company. We are doing quite well financially. The revenue for this quarter is higher than expected...",
    // add more fake transcripts as needed
  ];

  useEffect(() => {
    // Randomly select a fake transcript
    const selectedTranscript =
      fakeTranscripts[Math.floor(Math.random() * fakeTranscripts.length)];
    // Split the selected transcript into characters
    const characters = Array.from(selectedTranscript);

    let counter = 0;
    let liveTranscriptCopy = "";
    let intervalId = setInterval(() => {
      if (counter < characters.length) {
        liveTranscriptCopy += characters[counter];
        setLiveTranscript(liveTranscriptCopy);
        counter++;
      } else {
        clearInterval(intervalId);
      }
    }, 50); // delay of 100ms

    // Cleanup function to clear the interval when the component unmounts
    return () => clearInterval(intervalId);
  }, []);

  const generateDecibelData = (x) => {
    let data = [];
    let random = Mulberry32(123456789 + x);
    for (let i = 0; i < 50; i++) {
      data.push(Math.floor(random() * 30) + 10); // generate random values between 10 and 40
    }
    return data;
  };
  const generateDecibelGraph = (decibelData) => {
    return decibelData.map((decibel, i) => (
      <div
        key={i}
        className="w-1 bg-blue-500 mr-0.5"
        style={{ height: `${decibel}px` }}
      >
        &nbsp;
      </div>
    ));
  };

  // This is hardcoded data for proof of concept
  const data = [
    {
      timestamp: "00:00",
      topic: "Meeting Introduction",
      decibel: generateDecibelData(1),
      transcript:
        "This is the meeting introduction, we will be discussing several important topics today.",
    },
    {
      timestamp: "00:48",
      topic: "Discussing Quarterly Revenue",
      decibel: generateDecibelData(2),
      transcript:
        "We are discussing the quarterly revenue here, it appears our revenue has grown by 15% compared to the previous quarter.",
    },
    {
      timestamp: "01:35",
      topic: "Annual Sales Review",
      decibel: generateDecibelData(3),
      transcript:
        "Now we're reviewing the annual sales, there was a significant boost during the holiday season.",
    },
    {
      timestamp: "02:20",
      topic: "Operational Costs Analysis",
      decibel: generateDecibelData(4),
      transcript:
        "Moving on to the operational costs analysis, we have managed to reduce unnecessary expenses.",
    },
    {
      timestamp: "03:10",
      topic: "Employee Performance",
      decibel: generateDecibelData(5),
      transcript:
        "Let's talk about the employee performance, overall the team has done a great job.",
    },
    /*        { timestamp: '03:45', topic: 'New Marketing Strategies', decibel: generateDecibelData(6), transcript: "Our marketing team has proposed some new strategies that we'll discuss now." },
        { timestamp: '04:30', topic: 'Customer Feedback', decibel: generateDecibelData(7), transcript: "Let's go through some customer feedback that we've received." },
        { timestamp: '05:15', topic: 'Product Development', decibel: generateDecibelData(8), transcript: "Product development is going well and the new product line will be ready to launch next quarter." },
        { timestamp: '06:00', topic: 'Discussing Future Projects', decibel: generateDecibelData(9), transcript: "Now we are talking about the future projects, we have some exciting projects lined up." },
        { timestamp: '06:45', topic: 'Meeting Conclusion', decibel: generateDecibelData(10), transcript: "As we conclude the meeting, I want to thank everyone for their hard work and dedication." }, */
  ];

  return (
    <>
      <div className="p-4">
        <div className="flex justify-between border-b-2">
          <div className="w-1/4">Timestamp</div>
          <div className="w-1/4">Topic</div>
          <div className="w-1/4"></div>
        </div>
        {data.map((item, index) => (
          <div key={index} className="border-b-2 py-2">
            <div
              className="flex justify-between cursor-pointer"
              onClick={() => setOpenIndex(openIndex === index ? null : index)}
            >
              <div className="w-1/4">{item.timestamp}</div>
              <div className="w-1/4">
                {item.topic}{" "}
                <span
                  className={`inline-block transform transition-transform duration-200 ${
                    openIndex === index ? "rotate-90" : ""
                  }`}
                >
                  {">"}
                </span>
              </div>
              <div className="w-1/4 flex flex-row space-x-0.5">
                {generateDecibelGraph(item.decibel)}
              </div>
            </div>
            {openIndex === index && (
              <div className="mt-2 p-2">{item.transcript}</div>
            )}
          </div>
        ))}
        <div className="border-b-2 py-2 w-[90vw] max-w-[1280px]">
          <div className="flex justify-between">
            <div className="w-1/4">Live</div>
            <div className="w-1/4">Transcript</div>
            <div className="w-1/4 flex flex-row space-x-0.5">
              {generateDecibelGraph(generateDecibelData())}
            </div>
          </div>
          <div className="mt-2 p-2 bg-white temp-transcription">{props.transcriptionText}</div>
        </div>

      </div>
    </>
  );
}
