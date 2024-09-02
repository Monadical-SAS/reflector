import React, { useContext, useState, useEffect } from "react";
import SelectSearch from "react-select-search";
import { getZulipMessage, sendZulipMessage } from "../../../lib/zulip";
import { GetTranscript, GetTranscriptTopic } from "../../../api";
import "react-select-search/style.css";
import { DomainContext } from "../../../domainContext";

type ShareModal = {
  show: boolean;
  setShow: (show: boolean) => void;
  transcript: GetTranscript | null;
  topics: GetTranscriptTopic[] | null;
};

interface Stream {
  id: number;
  name: string;
  topics: string[];
}

interface SelectSearchOption {
  name: string;
  value: string;
}

const ShareModal = (props: ShareModal) => {
  const [stream, setStream] = useState<string | undefined>(undefined);
  const [topic, setTopic] = useState<string | undefined>(undefined);
  const [includeTopics, setIncludeTopics] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [streams, setStreams] = useState<Stream[]>([]);
  const { zulip_streams } = useContext(DomainContext);

  useEffect(() => {
    fetch(zulip_streams + "/streams.json")
      .then((response) => {
        if (!response.ok) {
          throw new Error("Network response was not ok");
        }
        return response.json();
      })
      .then((data) => {
        data = data.sort((a: Stream, b: Stream) =>
          a.name.localeCompare(b.name),
        );
        setStreams(data);
        setIsLoading(false);
        // data now contains the JavaScript object decoded from JSON
      })
      .catch((error) => {
        console.error("There was a problem with your fetch operation:", error);
      });
  }, []);

  const handleSendToZulip = () => {
    if (!props.transcript) return;

    const msg = getZulipMessage(props.transcript, props.topics, includeTopics);

    if (stream && topic) sendZulipMessage(stream, topic, msg);
  };

  if (props.show && isLoading) {
    return <div>Loading...</div>;
  }

  let streamOptions: SelectSearchOption[] = [];
  if (streams) {
    streams.forEach((stream) => {
      const value = stream.name;
      streamOptions.push({ name: value, value: value });
    });
  }

  return (
    <div className="absolute">
      {props.show && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
          <div className="relative top-20 mx-auto p-5 w-96 shadow-lg rounded-md bg-white">
            <div className="mt-3 text-center">
              <h3 className="font-bold text-xl">Send to Zulip</h3>

              {/* Checkbox for 'Include Topics' */}
              <div className="mt-4 text-left ml-5">
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    className="form-checkbox rounded border-gray-300 text-indigo-600 shadow-sm focus:border-indigo-300 focus:ring focus:ring-indigo-200 focus:ring-opacity-50"
                    checked={includeTopics}
                    onChange={(e) => setIncludeTopics(e.target.checked)}
                  />
                  <span className="ml-2">Include topics</span>
                </label>
              </div>

              <div className="flex items-center mt-4">
                <span className="mr-2">#</span>
                <SelectSearch
                  search={true}
                  options={streamOptions}
                  value={stream}
                  onChange={(val) => {
                    setTopic(undefined);
                    setStream(val.toString());
                  }}
                  placeholder="Pick a stream"
                />
              </div>

              {stream && (
                <>
                  <div className="flex items-center mt-4">
                    <span className="mr-2 invisible">#</span>
                    <SelectSearch
                      search={true}
                      options={
                        streams
                          .find((s) => s.name == stream)
                          ?.topics.sort((a: string, b: string) =>
                            a.localeCompare(b),
                          )
                          .map((t) => ({ name: t, value: t })) || []
                      }
                      value={topic}
                      onChange={(val) => setTopic(val.toString())}
                      placeholder="Pick a topic"
                    />
                  </div>
                </>
              )}

              <button
                className={`bg-blue-400 hover:bg-blue-500 focus-visible:bg-blue-500 text-white rounded py-2 px-4 mr-3 ${
                  !stream || !topic ? "opacity-50 cursor-not-allowed" : ""
                }`}
                disabled={!stream || !topic}
                onClick={() => {
                  handleSendToZulip();
                  props.setShow(false);
                }}
              >
                Send to Zulip
              </button>

              <button
                className="bg-red-500 hover:bg-red-700 focus-visible:bg-red-700 text-white rounded py-2 px-4 mt-4"
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
