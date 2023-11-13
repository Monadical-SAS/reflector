import React, { useRef, useEffect, useState } from "react";

import WaveSurfer from "wavesurfer.js";
import RecordPlugin from "../../lib/custom-plugins/record";
import CustomRegionsPlugin from "../../lib/custom-plugins/regions";

import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faMicrophone } from "@fortawesome/free-solid-svg-icons";

import { formatTime } from "../../lib/time";
import AudioInputsDropdown from "./audioInputsDropdown";
import { Option } from "react-dropdown";
import { waveSurferStyles } from "../../styles/recorder";
import { useError } from "../../(errors)/errorContext";

type RecorderProps = {
  setStream?: React.Dispatch<React.SetStateAction<MediaStream | null>>;
  onStop?: () => void;
  getAudioStream?: (deviceId) => Promise<MediaStream | null>;
  audioDevices?: Option[];
  mediaDuration?: number | null;
};

export default function Recorder(props: RecorderProps) {
  const waveformRef = useRef<HTMLDivElement>(null);
  const [wavesurfer, setWavesurfer] = useState<WaveSurfer | null>(null);
  const [record, setRecord] = useState<RecordPlugin | null>(null);
  const [isRecording, setIsRecording] = useState<boolean>(false);
  const [hasRecorded, setHasRecorded] = useState<boolean>(false);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [currentTime, setCurrentTime] = useState<number>(0);
  const [timeInterval, setTimeInterval] = useState<number | null>(null);
  const [duration, setDuration] = useState<number>(0);
  const [waveRegions, setWaveRegions] = useState<CustomRegionsPlugin | null>(
    null,
  );
  const [deviceId, setDeviceId] = useState<string | null>(null);
  const [recordStarted, setRecordStarted] = useState(false);
  const [showDevices, setShowDevices] = useState(false);
  const { setError } = useError();

  // Function used to setup keyboard shortcuts for the streamdeck
  const setupProjectorKeys = (): (() => void) => {
    if (!record) return () => {};

    const handleKeyPress = (event: KeyboardEvent) => {
      switch (event.key) {
        case "~":
          location.href = "";
          break;
        case ",":
          location.href = "/transcripts/new";
          break;
        case "!":
          if (record.isRecording()) return;
          handleRecClick();
          break;
        case "@":
          if (!record.isRecording()) return;
          handleRecClick();
          break;
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

  // Setup Shortcuts
  useEffect(() => {
    if (!record) return;

    return setupProjectorKeys();
  }, [record, deviceId]);

  // Waveform setup
  useEffect(() => {
    if (waveformRef.current) {
      const _wavesurfer = WaveSurfer.create({
        container: waveformRef.current,
        hideScrollbar: true,
        autoCenter: true,
        barWidth: 2,
        height: "auto",
        duration: props.mediaDuration || 1,

        ...waveSurferStyles.player,
      });

      const _wshack: any = _wavesurfer;
      _wshack.renderer.renderSingleCanvas = () => {};

      // styling
      const wsWrapper = _wavesurfer.getWrapper();
      wsWrapper.style.cursor = waveSurferStyles.playerStyle.cursor;
      wsWrapper.style.backgroundColor =
        waveSurferStyles.playerStyle.backgroundColor;
      wsWrapper.style.borderRadius = waveSurferStyles.playerStyle.borderRadius;

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
      if (props.onStop) props.onStop();
      record.stopRecording();
      if (screenMediaStream) {
        screenMediaStream.getTracks().forEach((t) => t.stop());
      }
      setIsRecording(false);
      setHasRecorded(true);
      setScreenMediaStream(null);
      setDestinationStream(null);
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

  const [screenMediaStream, setScreenMediaStream] =
    useState<MediaStream | null>(null);

  const handleRecordTabClick = async () => {
    if (!record) return console.log("no record");
    const stream: MediaStream = await navigator.mediaDevices.getDisplayMedia({
      video: true,
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        sampleRate: 44100,
      },
    });

    if (stream.getAudioTracks().length == 0) {
      setError(new Error("No audio track found in screen recording."));
      return;
    }
    setScreenMediaStream(stream);
  };

  const [destinationStream, setDestinationStream] =
    useState<MediaStream | null>(null);

  const startTabRecording = async () => {
    if (!screenMediaStream) return;
    if (!record) return;
    if (destinationStream !== null) return console.log("already recording");

    // connect mic audio (microphone)
    const micStream = await getCurrentStream();
    if (!micStream) {
      console.log("no microphone audio");
      return;
    }

    // Create MediaStreamSource nodes for the microphone and tab
    const audioContext = new AudioContext();
    const micSource = audioContext.createMediaStreamSource(micStream);
    const tabSource = audioContext.createMediaStreamSource(screenMediaStream);

    // Merge channels
    // XXX If the length is not the same, we do not receive audio in WebRTC.
    // So for now, merge the channels to have only one stereo source
    const channelMerger = audioContext.createChannelMerger(1);
    micSource.connect(channelMerger, 0, 0);
    tabSource.connect(channelMerger, 0, 0);

    // Create a MediaStreamDestination node
    const destination = audioContext.createMediaStreamDestination();
    channelMerger.connect(destination);

    // Use the destination's stream for the WebRTC connection
    setDestinationStream(destination.stream);
  };

  useEffect(() => {
    if (!record) return;
    if (!destinationStream) return;
    if (props.setStream) props.setStream(destinationStream);
    if (destinationStream) {
      record.startRecording(destinationStream);
      setIsRecording(true);
    }
  }, [record, destinationStream]);

  useEffect(() => {
    startTabRecording();
  }, [record, screenMediaStream]);

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
      setDeviceId(props.audioDevices[0].value);
    }
  }, [props.audioDevices]);

  return (
    <div className="flex items-center w-full relative">
      <div className="flex-grow items-end relative">
        <div
          ref={waveformRef}
          className="flex-grow rounded-lg md:rounded-xl h-20"
        ></div>
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
          >
            {isPlaying ? "Pause" : "Play"}
          </button>
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
          {!isRecording && (
            <button
              className={`${
                isRecording
                  ? "bg-red-400 hover:bg-red-500 focus-visible:bg-red-500"
                  : "bg-blue-400 hover:bg-blue-500 focus-visible:bg-blue-500"
              } text-white ml-2 md:ml:4 md:h-[78px] md:min-w-[100px] text-lg`}
              onClick={handleRecordTabClick}
            >
              Record
              <br />a tab
            </button>
          )}
          {props.audioDevices && props.audioDevices?.length > 0 && deviceId && (
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
                  deviceId={deviceId}
                />
              </div>
            </>
          )}
        </>
      )}
    </div>
  );
}
