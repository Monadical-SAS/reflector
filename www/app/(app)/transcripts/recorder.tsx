import React, { useRef, useEffect, useState } from "react";

import WaveSurfer from "wavesurfer.js";
import RecordPlugin from "../../lib/custom-plugins/record";

import { formatTime, formatTimeMs } from "../../lib/time";
import { waveSurferStyles } from "../../styles/recorder";
import { useError } from "../../(errors)/errorContext";
import FileUploadButton from "./fileUploadButton";
import useWebRTC from "./useWebRTC";
import useAudioDevice from "./useAudioDevice";
import { Box, Flex, IconButton, Menu, RadioGroup } from "@chakra-ui/react";
import { LuScreenShare, LuMic, LuPlay, LuCircleStop } from "react-icons/lu";
import { RECORD_A_MEETING_URL } from "../../api/urls";

type RecorderProps = {
  transcriptId: string;
  status: string;
};

export default function Recorder(props: RecorderProps) {
  const waveformRef = useRef<HTMLDivElement>(null);
  const [record, setRecord] = useState<RecordPlugin | null>(null);
  const [isRecording, setIsRecording] = useState<boolean>(false);

  const [duration, setDuration] = useState<number>(0);
  const [deviceId, setDeviceId] = useState<string | null>(null);
  const { setError } = useError();
  const [stream, setStream] = useState<MediaStream | null>(null);

  // Time tracking, iirc it was drifting without this. to be tested again.
  const [startTime, setStartTime] = useState(0);
  const [currentTime, setCurrentTime] = useState<number>(0);
  const [timeInterval, setTimeInterval] = useState<number | null>(null);

  const webRTC = useWebRTC(stream, props.transcriptId);

  const { audioDevices, getAudioStream } = useAudioDevice();

  // Function used to setup keyboard shortcuts for the streamdeck
  const setupProjectorKeys = (): (() => void) => {
    if (!record) return () => {};

    const handleKeyPress = (event: KeyboardEvent) => {
      switch (event.key) {
        case "~":
          location.href = "";
          break;
        case ",":
          location.href = RECORD_A_MEETING_URL;
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

      _wavesurfer.on("timeupdate", setCurrentTime);

      setRecord(_wavesurfer.registerPlugin(RecordPlugin.create()));

      return () => {
        _wavesurfer.destroy();
        setIsRecording(false);
        setCurrentTime(0);
      };
    }
  }, []);

  useEffect(() => {
    if (isRecording) {
      const interval = window.setInterval(() => {
        setCurrentTime(Date.now() - startTime);
      }, 1000);
      setTimeInterval(interval);
      return () => clearInterval(interval);
    } else {
      clearInterval(timeInterval as number);
      setCurrentTime((prev) => {
        setDuration(prev / 1000);
        return 0;
      });
    }
  }, [isRecording]);

  const handleRecClick = async () => {
    if (!record) return console.log("no record");

    if (record.isRecording()) {
      setStream(null);
      webRTC?.send(JSON.stringify({ cmd: "STOP" }));
      record.stopRecording();
      if (screenMediaStream) {
        screenMediaStream.getTracks().forEach((t) => t.stop());
      }
      setIsRecording(false);
      setScreenMediaStream(null);
      setDestinationStream(null);
    } else {
      const stream = await getMicrophoneStream();
      setStartTime(Date.now());

      setStream(stream);
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
    const micStream = await getMicrophoneStream();
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
    setStream(destinationStream);
    if (destinationStream) {
      record.startRecording(destinationStream);
      setIsRecording(true);
    }
  }, [record, destinationStream]);

  useEffect(() => {
    startTabRecording();
  }, [record, screenMediaStream]);

  const timeLabel = () => {
    if (isRecording) return formatTimeMs(currentTime);
    if (duration) return `${formatTimeMs(currentTime)}/${formatTime(duration)}`;
    return "";
  };

  const getMicrophoneStream = async () => {
    return deviceId && getAudioStream ? await getAudioStream(deviceId) : null;
  };

  useEffect(() => {
    if (audioDevices && audioDevices.length > 0) {
      setDeviceId(audioDevices[0].value);
    }
  }, [audioDevices]);

  return (
    <Flex className="flex items-center w-full relative">
      <IconButton
        aria-label={isRecording ? "Stop" : "Record"}
        variant={"ghost"}
        colorPalette={"blue"}
        mr={2}
        onClick={handleRecClick}
      >
        {isRecording ? <LuCircleStop /> : <LuPlay />}
      </IconButton>
      {!isRecording && (window as any).chrome && (
        <IconButton
          aria-label={"Record Tab"}
          variant={"ghost"}
          colorPalette={"blue"}
          disabled={isRecording}
          mr={2}
          onClick={handleRecordTabClick}
          size="sm"
        >
          <LuScreenShare />
        </IconButton>
      )}
      {audioDevices && audioDevices?.length > 0 && deviceId && !isRecording && (
        <Menu.Root>
          <Menu.Trigger asChild>
            <IconButton
              aria-label={"Switch microphone"}
              variant={"ghost"}
              disabled={isRecording}
              colorPalette={"blue"}
              mr={2}
              size="sm"
            >
              <LuMic />
            </IconButton>
          </Menu.Trigger>
          <Menu.Positioner>
            <Menu.Content>
              <Menu.RadioItemGroup
                value={deviceId}
                onValueChange={(e) => setDeviceId(e.value)}
              >
                {audioDevices.map((device) => (
                  <Menu.RadioItem key={device.value} value={device.value}>
                    <Menu.ItemIndicator />
                    {device.label}
                  </Menu.RadioItem>
                ))}
              </Menu.RadioItemGroup>
            </Menu.Content>
          </Menu.Positioner>
        </Menu.Root>
      )}
      <Box position="relative" flex={1}>
        <Box ref={waveformRef} height={14}></Box>
        <Box
          zIndex={50}
          backgroundColor="rgba(255, 255, 255, 0.5)"
          fontSize={"sm"}
          shadow={"0px 0px 4px 0px white"}
          position={"absolute"}
          right={0}
          bottom={0}
        >
          {timeLabel()}
        </Box>
      </Box>
    </Flex>
  );
}
