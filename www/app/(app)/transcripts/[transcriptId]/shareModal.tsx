import React, { useContext, useState, useEffect } from "react";
import SelectSearch from "react-select-search";
import { GetTranscript, GetTranscriptTopic } from "../../../api";
import "react-select-search/style.css";
import { DomainContext } from "../../../domainContext";
import useApi from "../../../lib/useApi";

type ShareModalProps = {
  show: boolean;
  setShow: (show: boolean) => void;
  transcript: GetTranscript | null;
  topics: GetTranscriptTopic[] | null;
};

interface Stream {
  stream_id: number;
  name: string;
}

interface Topic {
  name: string;
}

interface SelectSearchOption {
  name: string;
  value: string;
}

const ShareModal = (props: ShareModalProps) => {
  const [stream, setStream] = useState<string | undefined>(undefined);
  const [topic, setTopic] = useState<string | undefined>(undefined);
  const [includeTopics, setIncludeTopics] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [streams, setStreams] = useState<Stream[]>([]);
  const [topics, setTopics] = useState<Topic[]>([]);
  const api = useApi();

  useEffect(() => {
    const fetchZulipStreams = async () => {
      if (!api) return;

      try {
        const response = await api.v1ZulipGetStreams();
        setStreams(response);
        setIsLoading(false);
      } catch (error) {
        console.error("Error fetching Zulip streams:", error);
      }
    };

    fetchZulipStreams();
  }, [!api]);

  useEffect(() => {
    const fetchZulipTopics = async () => {
      if (!api || !stream) return;
      try {
        const selectedStream = streams.find((s) => s.name === stream);
        if (selectedStream) {
          const response = await api.v1ZulipGetTopics({
            streamId: selectedStream.stream_id,
          });
          setTopics(response);
        }
      } catch (error) {
        console.error("Error fetching Zulip topics:", error);
      }
    };

    fetchZulipTopics();
  }, [stream, streams, api]);

  const handleSendToZulip = async () => {
    if (!api || !props.transcript) return;

    if (stream && topic) {
      try {
        await api.v1TranscriptPostToZulip({
          transcriptId: props.transcript.id,
          stream,
          topic,
          includeTopics,
        });
      } catch (error) {
        console.log(error);
      }
    }
  };

  if (props.show && isLoading) {
    return <div>Loading...</div>;
  }

  const streamOptions: SelectSearchOption[] = streams.map((stream) => ({
    name: stream.name,
    value: stream.name,
  }));

  const topicOptions: SelectSearchOption[] = topics.map((topic) => ({
    name: topic.name,
    value: topic.name,
  }));

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
                    setTopic(undefined); // Reset topic when stream changes
                    setStream(val.toString());
                  }}
                  placeholder="Pick a stream"
                  onBlur={() => {}}
                  onFocus={() => {}}
                />
              </div>

              {stream && (
                <div className="flex items-center mt-4">
                  <span className="mr-2 invisible">#</span>
                  <SelectSearch
                    search={true}
                    options={topicOptions}
                    value={topic}
                    onChange={(val) => setTopic(val.toString())}
                    placeholder="Pick a topic"
                    onBlur={() => {}}
                    onFocus={() => {}}
                  />
                </div>
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
