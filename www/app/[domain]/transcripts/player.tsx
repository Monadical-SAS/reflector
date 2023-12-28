import React, { useRef, useEffect, useState } from "react";

import WaveSurfer from "wavesurfer.js";
import CustomRegionsPlugin from "../../lib/custom-plugins/regions";

import { formatTime } from "../../lib/time";
import { Topic } from "./webSocketTypes";
import { AudioWaveform } from "../../api";
import { waveSurferStyles } from "../../styles/recorder";

type PlayerProps = {
  topics: Topic[];
  useActiveTopic: [
    Topic | null,
    React.Dispatch<React.SetStateAction<Topic | null>>,
  ];
  waveform: AudioWaveform;
  media: HTMLMediaElement;
  mediaDuration: number;
};

export default function Player(props: PlayerProps) {
  const waveformRef = useRef<HTMLDivElement>(null);
  const [wavesurfer, setWavesurfer] = useState<WaveSurfer | null>(null);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [currentTime, setCurrentTime] = useState<number>(0);
  const [waveRegions, setWaveRegions] = useState<CustomRegionsPlugin | null>(
    null,
  );
  const [activeTopic, setActiveTopic] = props.useActiveTopic;
  const topicsRef = useRef(props.topics);
  // Waveform setup
  useEffect(() => {
    if (waveformRef.current) {
      // XXX duration is required to prevent recomputing peaks from audio
      // However, the current waveform returns only the peaks, and no duration
      // And the backend does not save duration properly.
      // So at the moment, we deduct the duration from the topics.
      // This is not ideal, but it works for now.
      const _wavesurfer = WaveSurfer.create({
        container: waveformRef.current,
        peaks: props.waveform,
        hideScrollbar: true,
        autoCenter: true,
        barWidth: 2,
        height: "auto",
        duration: props.mediaDuration,

        ...waveSurferStyles.player,
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

      setWaveRegions(_wavesurfer.registerPlugin(CustomRegionsPlugin.create()));

      _wavesurfer.toggleInteraction(true);

      _wavesurfer.setMediaElement(props.media);

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
    topicsRef.current = props.topics;
    renderMarkers();
  }, [props.topics, waveRegions]);

  const renderMarkers = () => {
    if (!waveRegions) return;

    waveRegions.clearRegions();

    for (let topic of topicsRef.current) {
      const content = document.createElement("div");
      content.setAttribute("style", waveSurferStyles.marker);
      content.onmouseover = () => {
        content.style.backgroundColor =
          waveSurferStyles.markerHover.backgroundColor;
        content.style.zIndex = "999";
        content.style.width = "300px";
      };
      content.onmouseout = () => {
        content.setAttribute("style", waveSurferStyles.marker);
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
    if (activeTopic) {
      wavesurfer?.setTime(activeTopic.timestamp);
    }
  }, [activeTopic]);

  const handlePlayClick = () => {
    wavesurfer?.playPause();
  };

  const timeLabel = () => {
    if (props.mediaDuration)
      return `${formatTime(currentTime)}/${formatTime(props.mediaDuration)}`;
    return "";
  };

  return (
    <div className="flex items-center w-full relative">
      <div className="flex-grow items-end relative">
        <div
          ref={waveformRef}
          className="flex-grow rounded-lg md:rounded-xl h-20"
        ></div>
        <div className="absolute right-2 bottom-0">{timeLabel()}</div>
      </div>

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
    </div>
  );
}
