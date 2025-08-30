import React, { useRef, useEffect, useState } from "react";

import WaveSurfer from "wavesurfer.js";
import RegionsPlugin from "wavesurfer.js/dist/plugins/regions.esm.js";

import { formatTime, formatTimeMs } from "../../lib/time";
import { Topic } from "./webSocketTypes";
import type { components } from "../../reflector-api";

type AudioWaveform = components["schemas"]["AudioWaveform"];
import { waveSurferStyles } from "../../styles/recorder";
import { Box, Flex, IconButton } from "@chakra-ui/react";
import { LuPause, LuPlay } from "react-icons/lu";

type PlayerProps = {
  topics: Topic[];
  useActiveTopic: [
    Topic | null,
    React.Dispatch<React.SetStateAction<Topic | null>>,
  ];
  waveform: AudioWaveform;
  media: HTMLMediaElement;
  mediaDuration: number | null;
};

export default function Player(props: PlayerProps) {
  const waveformRef = useRef<HTMLDivElement>(null);
  const [wavesurfer, setWavesurfer] = useState<WaveSurfer | null>(null);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [currentTime, setCurrentTime] = useState<number>(0);
  const [waveRegions, setWaveRegions] = useState<RegionsPlugin | null>(null);
  const [activeTopic, setActiveTopic] = props.useActiveTopic;
  const topicsRef = useRef(props.topics);
  const [firstRender, setFirstRender] = useState<boolean>(true);

  const keyHandler = (e) => {
    if (e.key == " ") {
      wavesurfer?.playPause();
    }
  };
  useEffect(() => {
    document.addEventListener("keyup", keyHandler);
    return () => {
      document.removeEventListener("keyup", keyHandler);
    };
  });

  // Waveform setup
  useEffect(() => {
    if (waveformRef.current) {
      const _wavesurfer = WaveSurfer.create({
        container: waveformRef.current,
        peaks: [props.waveform.data],
        height: "auto",
        duration: props.mediaDuration
          ? Math.floor(props.mediaDuration / 1000)
          : undefined,
        media: props.media,

        ...waveSurferStyles.playerSettings,
      });

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

      setWaveRegions(_wavesurfer.registerPlugin(RegionsPlugin.create()));

      _wavesurfer.toggleInteraction(true);

      setWavesurfer(_wavesurfer);

      return () => {
        _wavesurfer.destroy();
        setIsPlaying(false);
        setCurrentTime(0);
      };
    }
  }, []);

  useEffect(() => {
    if (!wavesurfer) return;
    if (!props.media) return;
    wavesurfer.setMediaElement(props.media);
  }, [props.media, wavesurfer]);

  useEffect(() => {
    if (!waveRegions) return;

    topicsRef.current = props.topics;
    if (firstRender) {
      setFirstRender(false);
      // wait for the waveform to render, if you don't markers will be stacked on top of each other
      // I tried to listen for the waveform to be ready but it didn't work
      setTimeout(() => {
        renderMarkers();
      }, 300);
    } else {
      renderMarkers();
    }
  }, [props.topics, waveRegions]);

  const renderMarkers = () => {
    if (!waveRegions) return;

    waveRegions.clearRegions();

    for (let topic of topicsRef.current) {
      const content = document.createElement("div");
      content.setAttribute("style", waveSurferStyles.marker);
      content.onmouseover = (e) => {
        content.style.backgroundColor =
          waveSurferStyles.markerHover.backgroundColor;
        content.style.width = "300px";
        if (content.parentElement) {
          content.parentElement.style.zIndex = "999";
        }
      };
      content.onmouseout = () => {
        content.setAttribute("style", waveSurferStyles.marker);
        if (content.parentElement) {
          content.parentElement.style.zIndex = "0";
        }
      };
      content.textContent = topic.title;

      const region = waveRegions.addRegion({
        start: topic.timestamp,
        content,
        drag: false,
        resize: false,
      });
      region.on("click", (e) => {
        e.stopPropagation();
        setActiveTopic(topic);
        wavesurfer?.setTime(region.start);
      });
    }
  };

  useEffect(() => {
    if (activeTopic) {
      wavesurfer?.setTime(activeTopic.timestamp);
    }
  }, [activeTopic]);

  const handlePlayClick = () => {
    wavesurfer?.playPause();
  };

  const timeLabel = () => {
    if (props.mediaDuration && Math.floor(props.mediaDuration / 1000) > 0)
      return `${formatTime(currentTime)}/${formatTimeMs(props.mediaDuration)}`;
    return "";
  };

  return (
    <Flex className="flex items-center w-full relative">
      <IconButton
        aria-label={isPlaying ? "Pause" : "Play"}
        variant={"ghost"}
        colorPalette={"blue"}
        mr={2}
        id="play-btn"
        onClick={handlePlayClick}
        size="sm"
      >
        {isPlaying ? <LuPause /> : <LuPlay />}
      </IconButton>

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
