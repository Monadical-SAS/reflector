import React, { useRef, useEffect, useState } from "react";

import WaveSurfer from "wavesurfer.js";
import RecordPlugin from "../lib/custom-plugins/record";

import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faDownload } from "@fortawesome/free-solid-svg-icons";

import Dropdown, { Option } from "react-dropdown";
import "react-dropdown/style.css";

import { formatTime } from "../lib/time";

const AudioInputsDropdown = (props: {
  audioDevices: Option[];
  setDeviceId: React.Dispatch<React.SetStateAction<string | null>>;
  disabled: boolean;
}) => {
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

export default function Recorder(props) {
  const waveformRef = useRef<HTMLDivElement>(null);
  const [wavesurfer, setWavesurfer] = useState<WaveSurfer | null>(null);
  const [record, setRecord] = useState<RecordPlugin | null>(null);
  const [isRecording, setIsRecording] = useState<boolean>(false);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [deviceId, setDeviceId] = useState<string | null>(null);
  const [currentTime, setCurrentTime] = useState<number>(0);
  const [timeInterval, setTimeInterval] = useState<number | null>(null);
  const [duration, setDuration] = useState<number>(0);

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
      setWavesurfer(_wavesurfer);
      return () => {
        _wavesurfer.destroy();
        setIsRecording(false);
        setIsPlaying(false);
      };
    }
  }, []);

  useEffect(() => {
    if (record) {
      return record.on("stopRecording", () => {
        const link = document.getElementById("download-recording");
        if (!link) return;

        link.setAttribute("href", record.getRecordedUrl());
        link.setAttribute("download", "reflector-recording.webm");
        link.style.visibility = "visible";
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

  const handleRecClick = async () => {
    if (!record) return console.log("no record");

    if (record.isRecording()) {
      props.onStop();
      record.stopRecording();
      setIsRecording(false);
      const playBtn = document.getElementById("play-btn");
      if (playBtn) playBtn.removeAttribute("disabled");
    } else {
      const stream = await props.getAudioStream(deviceId);
      props.setStream(stream);
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
    <div className="relative flex flex-col items-center justify-center max-w-[75vw] w-full">
      <div className="flex my-2 mx-auto">
        <AudioInputsDropdown
          audioDevices={props.audioDevices}
          setDeviceId={setDeviceId}
          disabled={isRecording}
        />
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
