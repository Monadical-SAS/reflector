import React, { useRef, useEffect, useState } from "react";

import WaveSurfer from "wavesurfer.js";

import Dropdown from "react-dropdown";
import "react-dropdown/style.css";

import CustomRecordPlugin from "./CustomRecordPlugin";

export default function Recorder(props) {
  const waveformRef = useRef();
  const [wavesurfer, setWavesurfer] = useState(null);
  const [record, setRecord] = useState(null);
  const [isRecording, setIsRecording] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [deviceId, setDeviceId] = useState(null);
  const [ddOptions, setDdOptions] = useState([]);

  useEffect(() => {
    document.getElementById("play-btn").disabled = true;

    navigator.mediaDevices.enumerateDevices().then((devices) => {
      const audioDevices = devices
        .filter((d) => d.kind === "audioinput")
        .map((d) => ({ value: d.deviceId, label: d.label }));

      if (audioDevices.length < 1) return console.log("no audio input devices");

      setDdOptions(audioDevices);
      setDeviceId(audioDevices[0].value);
    });

    if (waveformRef.current) {
      const _wavesurfer = WaveSurfer.create({
        container: waveformRef.current,
        waveColor: "#cc3347",
        progressColor: "#0178FFπ",
        cursorColor: "OrangeRed",
        hideScrollbar: true,
        autoCenter: true,
        barWidth: 2,
      });
      const wsWrapper = _wavesurfer.getWrapper();
      wsWrapper.style.cursor = "pointer";
      wsWrapper.style.backgroundColor = "lightgray";
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

  const handleRecClick = async () => {
    if (!record) return console.log("no record");

    if (record?.isRecording()) {

      props.serverData.peer.send(JSON.stringify({ cmd: "STOP" }));
      record.stopRecording();
      setIsRecording(false);
      document.getElementById("play-btn").disabled = false;
    } else {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { deviceId },
      });
      await record.startRecording(stream);
      props.setStream(stream);
      setIsRecording(true);
    }
  };

  const handlePlayClick = () => {
    wavesurfer?.playPause();
  };

  const handleDropdownChange = (e) => {
    setDeviceId(e.value);
  };

  return (
    <div className="flex flex-col items-center justify-center max-w-[75vw] w-full">
      <div className="flex my-2 mx-auto">
        <Dropdown
          options={ddOptions}
          onChange={handleDropdownChange}
          value={ddOptions[0]}
        />
        &nbsp;
        <button
          onClick={handleRecClick}
          data-color={isRecording ? "red" : "blue"}
        >
          {isRecording ? "Stop" : "Record"}
        </button>
        &nbsp;
        <button
          id="play-btn"
          onClick={handlePlayClick}
          data-color={isPlaying ? "orange" : "green"}
        >
          {isPlaying ? "Pause" : "Play"}
        </button>
      </div>
      <div ref={waveformRef} className="w-full"></div>
      {/* TODO: Download audio <a> tag */}
    </div>
  );
}
