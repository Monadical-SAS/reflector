import React, { useRef, useEffect, useState } from "react";

import WaveSurfer from "wavesurfer.js";

import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faDownload } from "@fortawesome/free-solid-svg-icons";

import Dropdown from "react-dropdown";
import "react-dropdown/style.css";

import CustomRecordPlugin from "./CustomRecordPlugin";

const AudioInputsDropdown = (props) => {
  const [ddOptions, setDdOptions] = useState([]);

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

  const handleRecClick = async () => {
    if (!record) return console.log("no record");

    if (record.isRecording()) {
      props.onStop();
      record.stopRecording();
      setIsRecording(false);
      document.getElementById("play-btn").disabled = false;
    } else {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          deviceId,
          noiseSuppression: false,
          echoCancellation: false,
        },
      });
      await record.startRecording(stream);
      props.setStream(stream);
      setIsRecording(true);
    }
  };

  const handlePlayClick = () => {
    wavesurfer?.playPause();
  };

  return (
    <div className="flex flex-col items-center justify-center max-w-[75vw] w-full">
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
      {/* TODO: current time / audio duration */}
    </div>
  );
}
