import React, { useState, useEffect } from "react";
import SelectSearch from "react-select-search";

type ShareModal = {
  show: boolean;
  setShow: (show: boolean) => void;
  title: string;
  url: string;
  summary: string;
};

const ShareModal = (props: ShareModal) => {
  const [stream, setStream] = useState(null);
  const [topic, setTopic] = useState(null);
  const [includeTranscript, setIncludeTranscript] = useState(false);
  const [includeSummary, setIncludeSummary] = useState(false);
  const [includeTopics, setIncludeTopics] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [streams, setStreams] = useState({});

  useEffect(() => {
    fetch("/streams.json")
      .then((response) => {
        if (!response.ok) {
          throw new Error("Network response was not ok");
        }
        return response.json();
      })
      .then((data) => {
        console.log("Stream data:", data);
        setStreams(data);
        setIsLoading(false);
        // data now contains the JavaScript object decoded from JSON
      })
      .catch((error) => {
        console.error("There was a problem with your fetch operation:", error);
      });
  }, []);

  const handleSendToZulip = () => {
    const message = `### Reflector Recording\n\n**[${props.title}](${props.url})**\n\n${props.summary}`;

    alert("Send to zulip");
  };

  if (props.show && isLoading) {
    return <div>Loading...</div>;
  }

  return (
    <div>
      {props.show && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full">
          <div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
            <div className="mt-3 text-center">
              {/*
                            <Select
                                options={streamOptions}
                                onChange={setStream}
                                placeholder="Select Stream"
                            />
                            <Select
                                options={topicOptions}
                                onChange={setTopic}
                                placeholder="Select Topic"
                                className="mt-4"
            /> */}
              <div className="flex flex-col mt-4">
                <label>
                  <input
                    type="checkbox"
                    checked={includeTranscript}
                    onChange={(e) => setIncludeTranscript(e.target.checked)}
                  />
                  Include Transcript
                </label>
                <label>
                  <input
                    type="checkbox"
                    checked={includeSummary}
                    onChange={(e) => setIncludeSummary(e.target.checked)}
                  />
                  Include Summary
                </label>
                <label>
                  <input
                    type="checkbox"
                    checked={includeTopics}
                    onChange={(e) => setIncludeTopics(e.target.checked)}
                  />
                  Include Topics
                </label>
              </div>
              <button
                className="bg-green-500 hover:bg-green-700 text-white font-bold py-2 px-4 rounded mt-4"
                onClick={handleSendToZulip}
              >
                Send to Zulip
              </button>
              <button
                className="bg-red-500 hover:bg-red-700 text-white font-bold py-2 px-4 rounded mt-4"
                onClick={() => props.setShow(false)}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ShareModal;
