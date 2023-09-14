import React, { useRef, useEffect, useState } from "react";

import WaveSurfer from "wavesurfer.js";
import RecordPlugin from "../lib/custom-plugins/record";
import CustomRegionsPlugin from "../lib/custom-plugins/regions";

import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faDownload } from "@fortawesome/free-solid-svg-icons";

import Dropdown, { Option } from "react-dropdown";
import "react-dropdown/style.css";

import { formatTime } from "../lib/time";
import { Topic } from "./webSocketTypes";
import { useError } from "../(errors)/errorContext";

import { isProjector } from "../lib/utils";

const AudioInputsDropdown: React.FC<{
  audioDevices: Option[];
  setDeviceId: React.Dispatch<React.SetStateAction<string | null>>;
  disabled: boolean;
}> = (props) => {
  const [ddOptions, setDdOptions] = useState<Option[]>([]);

  useEffect(() => {
    setDdOptions(props.audioDevices);
    props.setDeviceId(
      props.audioDevices.length > 0 ? props.audioDevices[0].value : null,
    );
  }, [props.audioDevices]);

  const handleDropdownChange = (option: Option) => {
    props.setDeviceId(option.value);
  };

  return (
    <Dropdown
      options={ddOptions}
      onChange={handleDropdownChange}
      value={ddOptions[0]}
      disabled={props.disabled}
    />
  );
};

type RecorderProps = {
  setStream: React.Dispatch<React.SetStateAction<MediaStream | null>>;
  onStop: () => void;
  topics: Topic[];
  getAudioStream: (deviceId: string | null) => Promise<MediaStream | null>;
  audioDevices: Option[];
  useActiveTopic: [
    Topic | null,
    React.Dispatch<React.SetStateAction<Topic | null>>,
  ];
};

export default function Recorder(props: RecorderProps) {
  const waveformRef = useRef<HTMLDivElement>(null);
  const [wavesurfer, setWavesurfer] = useState<WaveSurfer | null>(null);
  const [record, setRecord] = useState<RecordPlugin | null>(null);
  const [isRecording, setIsRecording] = useState<boolean>(false);
  const [hasRecorded, setHasRecorded] = useState<boolean>(false);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [deviceId, setDeviceId] = useState<string | null>(null);
  const [currentTime, setCurrentTime] = useState<number>(0);
  const [timeInterval, setTimeInterval] = useState<number | null>(null);
  const [duration, setDuration] = useState<number>(0);
  const [waveRegions, setWaveRegions] = useState<CustomRegionsPlugin | null>(
    null,
  );

  const [activeTopic, setActiveTopic] = props.useActiveTopic;

  const topicsRef = useRef(props.topics);
  const { setError } = useError();

  // Function used to setup keyboard shortcuts for the streamdeck when running in projector mode
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
    const playBtn = document.getElementById("play-btn");
    if (playBtn) playBtn.setAttribute("disabled", "true");

    if (waveformRef.current) {
      const _wavesurfer = WaveSurfer.create({
        container: waveformRef.current,
        waveColor: "white",
        progressColor: "white",
        cursorColor: "transparent",
        hideScrollbar: true,
        autoCenter: true,
        barWidth: 2,
        height: 60,
      });
      const wsWrapper = _wavesurfer.getWrapper();
      // wsWrapper.style.cursor = "pointer";
      wsWrapper.style.borderRadius = "15px";

      _wavesurfer.on("play", () => {
        setIsPlaying(true);
      });
      _wavesurfer.on("pause", () => {
        setIsPlaying(false);
      });
      _wavesurfer.on("timeupdate", setCurrentTime);

      setRecord(
        _wavesurfer.registerPlugin(RecordPlugin.create({ waveColor: "white" })),
      );
      setWaveRegions(_wavesurfer.registerPlugin(CustomRegionsPlugin.create()));

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
        border-radius: 0 3px 3px 0;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        transition: width 100ms linear;
      `,
      );
      content.onmouseover = () => {
        content.style.backgroundColor = "#feb082";
        content.style.zIndex = "999";
        content.style.width = "300px";
      };
      content.onmouseout = () => {
        content.style.backgroundColor = "#4551e5";
        content.style.zIndex = "0";
        content.style.width = "100px";
      };
      content.textContent = topic.title;
      content.style.backgroundColor = "#feb082";

      const region = waveRegions.addRegion({
        start: topic.timestamp,
        content,
        color: "white",
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

    let cleanup: (() => void) | undefined;

    if (isProjector()) {
      cleanup = setupProjectorKeys();
    }

    return () => {
      record.on("stopRecording", () => {
        const link = document.getElementById("download-recording");
        if (!link) return;

        link.setAttribute("href", record.getRecordedUrl());
        link.setAttribute("download", "reflector-recording.webm");
        link.style.visibility = "visible";
        renderMarkers();
      });

      if (cleanup) cleanup();
    };
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
      props.onStop();
      record.stopRecording();
      setIsRecording(false);
      setHasRecorded(true);
    } else {
      const stream = await props.getAudioStream(deviceId);
      props.setStream(stream);
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

  return (
    <div className="relative w-full">
      <div
        ref={waveformRef}
        className="w-full shadow-xl rounded-2xl bg-white/10"
      ></div>
      <div className="absolute bottom-0 right-2 text-xs text-black">
        {isRecording && (
          <div className="inline-block bg-white rounded-full w-2 h-2 my-auto mr-1 animate-ping"></div>
        )}
        {timeLabel()}
      </div>
    </div>
  );
}
