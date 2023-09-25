import React, { useRef, useEffect, useState } from "react";

import WaveSurfer from "wavesurfer.js";
import RecordPlugin from "../lib/custom-plugins/record";
import CustomRegionsPlugin from "../lib/custom-plugins/regions";

import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faMicrophone } from "@fortawesome/free-solid-svg-icons";
import { faDownload } from "@fortawesome/free-solid-svg-icons";

import { formatTime } from "../lib/time";
import { Topic } from "./webSocketTypes";
import { AudioWaveform } from "../api";
import AudioInputsDropdown from "./audioInputsDropdown";
import { Option } from "react-dropdown";
import { useError } from "../(errors)/errorContext";

type RecorderProps = {
  setStream?: React.Dispatch<React.SetStateAction<MediaStream | null>>;
  onStop?: () => void;
  topics: Topic[];
  getAudioStream?: (deviceId) => Promise<MediaStream | null>;
  audioDevices?: Option[];
  useActiveTopic: [
    Topic | null,
    React.Dispatch<React.SetStateAction<Topic | null>>,
  ];
  waveform?: AudioWaveform | null;
  isPastMeeting: boolean;
  transcriptId?: string | null;
};

export default function Recorder(props: RecorderProps) {
  const waveformRef = useRef<HTMLDivElement>(null);
  const [wavesurfer, setWavesurfer] = useState<WaveSurfer | null>(null);
  const [record, setRecord] = useState<RecordPlugin | null>(null);
  const [isRecording, setIsRecording] = useState<boolean>(false);
  const [hasRecorded, setHasRecorded] = useState<boolean>(props.isPastMeeting);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [currentTime, setCurrentTime] = useState<number>(0);
  const [timeInterval, setTimeInterval] = useState<number | null>(null);
  const [duration, setDuration] = useState<number>(0);
  const [waveRegions, setWaveRegions] = useState<CustomRegionsPlugin | null>(
    null,
  );
  const [deviceId, setDeviceId] = useState<string | null>(null);
  const [recordStarted, setRecordStarted] = useState(false);
  const [activeTopic, setActiveTopic] = props.useActiveTopic;
  const topicsRef = useRef(props.topics);
  const [showDevices, setShowDevices] = useState(false);
  const { setError } = useError();

  // Function used to setup keyboard shortcuts for the streamdeck
  const setupProjectorKeys = (): (() => void) => {
    if (!record) return () => {};

    const handleKeyPress = (event: KeyboardEvent) => {
      switch (event.key) {
        case "~":
          location.reload();
          break;
        case "!":
          if (record.isRecording()) return;
          handleRecClick();
          break;
        case "@":
          if (!record.isRecording()) return;
          handleRecClick();
          break;
        case "%":
          setError(new Error("Error triggered by '%' shortcut"));
          break;
        case "^":
          throw new Error("Unhandled Exception thrown by '^' shortcut");
        case "(":
          location.href = "/login";
          break;
        case ")":
          location.href = "/logout";
          break;
        default:
          break;
      }
    };

    document.addEventListener("keydown", handleKeyPress);

    // Return the cleanup function
    return () => {
      document.removeEventListener("keydown", handleKeyPress);
    };
  };

  useEffect(() => {
    if (waveformRef.current) {
      const _wavesurfer = WaveSurfer.create({
        container: waveformRef.current,
        waveColor: "#777",
        progressColor: "#222",
        cursorColor: "OrangeRed",
        hideScrollbar: true,
        autoCenter: true,
        barWidth: 2,
        height: "auto",
        url: props.transcriptId
          ? `${process.env.NEXT_PUBLIC_API_URL}/v1/transcripts/${props.transcriptId}/audio/mp3`
          : undefined,
      });

      const wsWrapper = _wavesurfer.getWrapper();
      wsWrapper.style.cursor = "pointer";
      wsWrapper.style.backgroundColor = "#e0c3fc42";
      wsWrapper.style.borderRadius = "15px";

      _wavesurfer.on("play", () => {
        setIsPlaying(true);
      });
      _wavesurfer.on("pause", () => {
        setIsPlaying(false);
      });
      _wavesurfer.on("timeupdate", setCurrentTime);

      setRecord(_wavesurfer.registerPlugin(RecordPlugin.create()));
      setWaveRegions(_wavesurfer.registerPlugin(CustomRegionsPlugin.create()));

      if (props.transcriptId) _wavesurfer.toggleInteraction(true);

      setWavesurfer(_wavesurfer);
      return () => {
        _wavesurfer.destroy();
        setIsRecording(false);
        setIsPlaying(false);
        setCurrentTime(0);
      };
    }
  }, []);

  useEffect(() => {
    topicsRef.current = props.topics;
    if (!isRecording) renderMarkers();
  }, [props.topics]);

  const renderMarkers = () => {
    if (!waveRegions) return;

    waveRegions.clearRegions();
    for (let topic of topicsRef.current) {
      const content = document.createElement("div");
      content.setAttribute(
        "style",
        `
        position: absolute;
        border-left: solid 1px orange;
        padding: 0 2px 0 5px;
        font-size: 0.7rem;
        width: 100px;
        max-width: fit-content;
        cursor: pointer;
        background-color: white;
        border-radius: 0 3px 3px 0;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        transition: width 100ms linear;
      `,
      );
      content.onmouseover = () => {
        content.style.backgroundColor = "orange";
        content.style.zIndex = "999";
        content.style.width = "300px";
      };
      content.onmouseout = () => {
        content.style.backgroundColor = "white";
        content.style.zIndex = "0";
        content.style.width = "100px";
      };
      content.textContent = topic.title;

      const region = waveRegions.addRegion({
        start: topic.timestamp,
        content,
        color: "f00",
        drag: false,
      });
      region.on("click", (e) => {
        e.stopPropagation();
        setActiveTopic(topic);
        wavesurfer?.setTime(region.start);
      });
    }
  };

  useEffect(() => {
    if (!record) return;

    return setupProjectorKeys();
  }, [record, deviceId]);

  useEffect(() => {
    if (!record) return;

    return record.on("stopRecording", () => {
      const link = document.getElementById("download-recording");
      if (!link) return;

      link.setAttribute("href", record.getRecordedUrl());
      link.setAttribute("download", "reflector-recording.webm");
      link.style.visibility = "visible";
      renderMarkers();
    });
  }, [record]);

  useEffect(() => {
    if (isRecording) {
      const interval = window.setInterval(() => {
        setCurrentTime((prev) => prev + 1);
      }, 1000);
      setTimeInterval(interval);
      return () => clearInterval(interval);
    } else {
      clearInterval(timeInterval as number);
      setCurrentTime((prev) => {
        setDuration(prev);
        return 0;
      });
    }
  }, [isRecording]);

  useEffect(() => {
    if (activeTopic) {
      wavesurfer?.setTime(activeTopic.timestamp);
    }
  }, [activeTopic]);

  const handleRecClick = async () => {
    if (!record) return console.log("no record");

    if (record.isRecording()) {
      if (props.onStop) props.onStop();
      record.stopRecording();
      setIsRecording(false);
      setHasRecorded(true);
    } else {
      const stream = await getCurrentStream();

      if (props.setStream) props.setStream(stream);
      waveRegions?.clearRegions();
      if (stream) {
        await record.startRecording(stream);
        setIsRecording(true);
      }
    }
  };

  const handlePlayClick = () => {
    wavesurfer?.playPause();
  };

  const timeLabel = () => {
    if (isRecording) return formatTime(currentTime);
    if (duration) return `${formatTime(currentTime)}/${formatTime(duration)}`;
    return "";
  };

  const getCurrentStream = async () => {
    setRecordStarted(true);
    return deviceId && props.getAudioStream
      ? await props.getAudioStream(deviceId)
      : null;
  };

  useEffect(() => {
    if (props.audioDevices && props.audioDevices.length > 0) {
      setDeviceId[props.audioDevices[0].value];
    }
  }, [props.audioDevices]);

  return (
    <div className="flex items-center w-full relative">
      <div className="flex-grow items-end relative">
        <div ref={waveformRef} className="flex-grow rounded-2xl h-20"></div>
        <div className="absolute right-2 bottom-0">
          {isRecording && (
            <div className="inline-block bg-red-500 rounded-full w-2 h-2 my-auto mr-1 animate-ping"></div>
          )}
          {timeLabel()}
        </div>
      </div>

      {hasRecorded && (
        <>
          <button
            className={`${
              isPlaying
                ? "bg-orange-400 hover:bg-orange-500 focus-visible:bg-orange-500"
                : "bg-green-400 hover:bg-green-500 focus-visible:bg-green-500"
            } text-white ml-2 md:ml:4 md:h-[78px] md:min-w-[100px] text-lg`}
            id="play-btn"
            onClick={handlePlayClick}
            disabled={isRecording}
          >
            {isPlaying ? "Pause" : "Play"}
          </button>

          {props.transcriptId && (
            <a
              title="Download recording"
              className="text-center cursor-pointer text-blue-400 hover:text-blue-700 ml-2 md:ml:4 p-2 rounded-lg outline-blue-400"
              href={`${process.env.NEXT_PUBLIC_API_URL}/v1/transcripts/${props.transcriptId}/audio/mp3`}
            >
              <FontAwesomeIcon icon={faDownload} className="h-5 w-auto" />
            </a>
          )}

          {!props.transcriptId && (
            <a
              id="download-recording"
              title="Download recording"
              className="invisible text-center text-blue-400 hover:text-blue-700 ml-2 md:ml:4 p-2 rounded-lg outline-blue-400"
            >
              <FontAwesomeIcon icon={faDownload} className="h-5 w-auto" />
            </a>
          )}
        </>
      )}
      {!hasRecorded && (
        <>
          <button
            className={`${
              isRecording
                ? "bg-red-400 hover:bg-red-500 focus-visible:bg-red-500"
                : "bg-blue-400 hover:bg-blue-500 focus-visible:bg-blue-500"
            } text-white ml-2 md:ml:4 md:h-[78px] md:min-w-[100px] text-lg`}
            onClick={handleRecClick}
            disabled={isPlaying}
          >
            {isRecording ? "Stop" : "Record"}
          </button>
          {props.audioDevices && props.audioDevices?.length > 0 && (
            <>
              <button
                className="text-center text-blue-400 hover:text-blue-700 ml-2 md:ml:4 p-2 rounded-lg focus-visible:outline outline-blue-400"
                onClick={() => setShowDevices((prev) => !prev)}
              >
                <FontAwesomeIcon icon={faMicrophone} className="h-5 w-auto" />
              </button>
              <div
                className={`absolute z-20 bottom-[-1rem] right-0 bg-white rounded ${
                  showDevices ? "visible" : "invisible"
                }`}
              >
                <AudioInputsDropdown
                  setDeviceId={setDeviceId}
                  audioDevices={props.audioDevices}
                  disabled={recordStarted}
                  hide={() => setShowDevices(false)}
                />
              </div>
            </>
          )}
        </>
      )}
    </div>
  );
}
