import React, { useRef, useEffect, useState } from "react";

import WaveSurfer from "wavesurfer.js";

import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faDownload } from "@fortawesome/free-solid-svg-icons";

import Dropdown from "react-dropdown";
import "react-dropdown/style.css";

import CustomRecordPlugin from "../lib/CustomRecordPlugin";
import { formatTime } from "../lib/time";

const AudioInputsDropdown = (props) => {
  const [ddOptions, setDdOptions] = useState([]);

  useEffect(() => {
    setDdOptions(props.audioDevices);
    props.setDeviceId(
      props.audioDevices.length > 0 ? props.audioDevices[0].value : null,
    );
  }, [props.audioDevices]);

  const handleDropdownChange = (e) => {
    props.setDeviceId(e.value);
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
  const waveformRef = useRef();
  const [wavesurfer, setWavesurfer] = useState(null);
  const [record, setRecord] = useState(null);
  const [isRecording, setIsRecording] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [deviceId, setDeviceId] = useState(null);
  const [currentTime, setCurrentTime] = useState(0);
  const [timeInterval, setTimeInterval] = useState(null);
  const [duration, setDuration] = useState(0);

  useEffect(() => {
    document.getElementById("play-btn").disabled = true;

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

      setRecord(_wavesurfer.registerPlugin(CustomRecordPlugin.create()));
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
        link.href = record.getRecordedUrl();
        link.download = "reflector-recording.webm";
        link.style.visibility = "visible";
      });
    }
  }, [record]);

  useEffect(() => {
    if (isRecording) {
      const interval = setInterval(() => {
        setCurrentTime((prev) => prev + 1);
      }, 1000);
      setTimeInterval(interval);
      return () => clearInterval(interval);
    } else {
      clearInterval(timeInterval);
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
      document.getElementById("play-btn").disabled = false;
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
    else if (duration)
      return `${formatTime(currentTime)}/${formatTime(duration)}`;
    else "";
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
