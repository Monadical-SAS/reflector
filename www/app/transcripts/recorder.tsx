import React, { useRef, useEffect, useState } from "react";

import WaveSurfer from "wavesurfer.js";
import RecordPlugin from "../lib/custom-plugins/record";
import CustomRegionsPlugin from "../lib/custom-plugins/regions";

import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faDownload } from "@fortawesome/free-solid-svg-icons";

import Dropdown, { Option } from "react-dropdown";
import "react-dropdown/style.css";

import { formatTime } from "../lib/time";

const AudioInputsDropdown: React.FC<{
  setDeviceId: React.Dispatch<React.SetStateAction<string | null>>;
  disabled: boolean;
}> = (props) => {
  const [ddOptions, setDdOptions] = useState<Array<Option>>([]);

  useEffect(() => {
    const init = async () => {
      // Request permission to use audio inputs
      await navigator.mediaDevices
        .getUserMedia({ audio: true })
        .then((stream) => stream.getTracks().forEach((t) => t.stop()));

      const devices = await navigator.mediaDevices.enumerateDevices();
      const audioDevices = devices
        .filter((d) => d.kind === "audioinput" && d.deviceId != "")
        .map((d) => ({ value: d.deviceId, label: d.label }));

      if (audioDevices.length < 1) return console.log("no audio input devices");

      setDdOptions(audioDevices);
      props.setDeviceId(audioDevices[0].value);
    };
    init();
  }, []);

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

export default function Recorder(props: any) {
  const waveformRef = useRef<HTMLDivElement>(null);
  const [wavesurfer, setWavesurfer] = useState<WaveSurfer | null>(null);
  const [record, setRecord] = useState<RecordPlugin | null>(null);
  const [isRecording, setIsRecording] = useState<boolean>(false);
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

  useEffect(() => {
    const playBtn = document.getElementById("play-btn");
    if (playBtn) playBtn.setAttribute("disabled", "true");

    if (waveformRef.current) {
      const _wavesurfer = WaveSurfer.create({
        container: waveformRef.current,
        waveColor: "#777",
        progressColor: "#222",
        cursorColor: "OrangeRed",
        hideScrollbar: true,
        autoCenter: true,
        barWidth: 2,
        height: 90,
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
    if (record) {
      return record.on("stopRecording", () => {
        const link = document.getElementById("download-recording");
        if (!link) return;

        link.setAttribute("href", record.getRecordedUrl());
        link.setAttribute("download", "reflector-recording.webm");
        link.style.visibility = "visible";
        renderMarkers();
      });
    }
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
      const playBtn = document.getElementById("play-btn");
      if (playBtn) playBtn.removeAttribute("disabled");
    } else {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          deviceId: deviceId as string,
          noiseSuppression: false,
          echoCancellation: false,
        },
      });
      await record.startRecording(stream);
      props.setStream(stream);
      setIsRecording(true);
      waveRegions?.clearRegions();
    }
  };

  const handlePlayClick = () => {
    wavesurfer?.playPause();
  };

  const timeLabel = () => {
    if (isRecording) return formatTime(currentTime);
    else if (duration)
      return `${formatTime(currentTime)}/${formatTime(duration)}`;
    else "";
  };

  return (
    <div className="relative flex flex-col items-center justify-center max-w-[75vw] w-full">
      <div className="flex my-2 mx-auto">
        <AudioInputsDropdown setDeviceId={setDeviceId} disabled={isRecording} />
        &nbsp;
        <button
          className="w-20"
          onClick={handleRecClick}
          data-color={isRecording ? "red" : "blue"}
          disabled={!deviceId}
        >
          {isRecording ? "Stop" : "Record"}
        </button>
        &nbsp;
        <button
          className="w-20"
          id="play-btn"
          onClick={handlePlayClick}
          data-color={isPlaying ? "orange" : "green"}
        >
          {isPlaying ? "Pause" : "Play"}
        </button>
        <a
          id="download-recording"
          title="Download recording"
          className="invisible w-9 m-auto text-center cursor-pointer text-blue-300 hover:text-blue-700"
        >
          <FontAwesomeIcon icon={faDownload} />
        </a>
      </div>
      <div ref={waveformRef} className="w-full shadow-xl rounded-2xl"></div>
      <div className="absolute bottom-0 right-2 text-xs text-black">
        {isRecording && (
          <div className="inline-block bg-red-500 rounded-full w-2 h-2 my-auto mr-1 animate-ping"></div>
        )}
        {timeLabel()}
      </div>
    </div>
  );
}
