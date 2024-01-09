import { useEffect, useRef, useState } from "react";
import useMp3 from "../../useMp3";
import { formatTime } from "../../../../lib/time";
import SoundWaveCss from "./soundWaveCss";
import { TimeSlice } from "./types";
import {
  BoxProps,
  Button,
  Wrap,
  Text,
  WrapItem,
  Kbd,
  Skeleton,
} from "@chakra-ui/react";

type TopicPlayer = {
  transcriptId: string;
  selectedTime: TimeSlice | undefined;
  topicTime: TimeSlice | undefined;
};

const TopicPlayer = ({
  transcriptId,
  selectedTime,
  topicTime,
  ...chakraProps
}: TopicPlayer & BoxProps) => {
  const mp3 = useMp3(transcriptId);
  const [isPlaying, setIsPlaying] = useState(false);
  const [endTopicCallback, setEndTopicCallback] = useState<() => void>();
  const [endSelectionCallback, setEndSelectionCallback] =
    useState<() => void>();
  const [showTime, setShowTime] = useState("");
  const playButton = useRef<HTMLButtonElement>(null);

  const keyHandler = (e) => {
    if (e.key == " ") {
      if (e.target.id != "playButton") {
        if (isPlaying) {
          mp3.media?.pause();
          setIsPlaying(false);
        } else {
          mp3.media?.play();
          setIsPlaying(true);
        }
      }
    } else if (selectedTime && e.key == ",") {
      playSelection();
    }
  };
  useEffect(() => {
    document.addEventListener("keyup", keyHandler);
    return () => {
      document.removeEventListener("keyup", keyHandler);
    };
  });

  const calcShowTime = () => {
    if (!topicTime) return;
    setShowTime(
      `${
        mp3.media?.currentTime
          ? formatTime(mp3.media?.currentTime - topicTime.start)
          : "00:00"
      }/${formatTime(topicTime.end - topicTime.start)}`,
    );
  };

  useEffect(() => {
    let i;
    if (isPlaying) {
      i = setInterval(calcShowTime, 1000);
    }
    return () => i && clearInterval(i);
  }, [isPlaying]);

  useEffect(() => {
    setEndTopicCallback(
      () =>
        function () {
          if (
            !topicTime ||
            !mp3.media ||
            !(mp3.media.currentTime >= topicTime.end)
          )
            return;
          mp3.media.pause();
          setIsPlaying(false);
          mp3.media.currentTime = topicTime.start;
          calcShowTime();
        },
    );
    if (mp3.media) {
      playButton.current?.focus();
      mp3.media?.pause();
      // there's no callback on pause but apparently changing the time while palying doesn't work... so here is a timeout
      setTimeout(() => {
        if (mp3.media) {
          if (!topicTime) return;
          mp3.media.currentTime = topicTime.start;
          setShowTime(`00:00/${formatTime(topicTime.end - topicTime.start)}`);
        }
      }, 10);
      setIsPlaying(false);
    }
  }, [!mp3.media, topicTime?.start, topicTime?.end]);

  useEffect(() => {
    endTopicCallback &&
      mp3.media &&
      mp3.media.addEventListener("timeupdate", endTopicCallback);

    return () => {
      endTopicCallback &&
        mp3.media &&
        mp3.media.removeEventListener("timeupdate", endTopicCallback);
    };
  }, [endTopicCallback]);

  const playSelection = (e?) => {
    e?.preventDefault();
    e?.target?.blur();
    if (mp3.media && selectedTime?.start !== undefined) {
      mp3.media.currentTime = selectedTime.start;
      calcShowTime();
      setEndSelectionCallback(
        () =>
          function () {
            if (
              mp3.media &&
              selectedTime.end &&
              mp3.media.currentTime >= selectedTime.end
            ) {
              mp3.media.pause();
              setIsPlaying(false);

              setEndSelectionCallback(() => {});
            }
          },
      );
      mp3.media.play();
      setIsPlaying(true);
    }
  };

  useEffect(() => {
    endSelectionCallback &&
      mp3.media &&
      mp3.media.addEventListener("timeupdate", endSelectionCallback);
    return () => {
      endSelectionCallback &&
        mp3.media &&
        mp3.media.removeEventListener("timeupdate", endSelectionCallback);
    };
  }, [endSelectionCallback]);

  const playTopic = (e) => {
    e?.preventDefault();
    e?.target?.blur();
    if (!topicTime) return;
    if (mp3.media) {
      mp3.media.currentTime = topicTime.start;
      mp3.media.play();
      setIsPlaying(true);
      endSelectionCallback &&
        mp3.media.removeEventListener("timeupdate", endSelectionCallback);
    }
  };

  const playCurrent = (e) => {
    e.preventDefault();
    e?.target?.blur();

    mp3.media?.play();
    setIsPlaying(true);
  };

  const pause = (e) => {
    e.preventDefault();
    e?.target?.blur();

    mp3.media?.pause();
    setIsPlaying(false);
  };

  const isLoaded = !!(mp3.media && topicTime);
  return (
    <Skeleton
      isLoaded={isLoaded}
      h={isLoaded ? "auto" : "40px"}
      fadeDuration={1}
      w={isLoaded ? "auto" : "container.md"}
      margin="auto"
      {...chakraProps}
    >
      <Wrap spacing="4" justify="center" align="center">
        <WrapItem>
          <SoundWaveCss playing={isPlaying} />
          <Text fontSize="sm" pt="1" pl="2">
            {showTime}
          </Text>
        </WrapItem>
        <WrapItem>
          <Button onClick={playTopic} colorScheme="blue">
            Play from start
          </Button>
        </WrapItem>
        <WrapItem>
          {!isPlaying ? (
            <Button
              onClick={playCurrent}
              ref={playButton}
              id="playButton"
              colorScheme="blue"
              w="120px"
            >
              <Kbd color="blue.600">Space</Kbd>&nbsp;Play
            </Button>
          ) : (
            <Button
              onClick={pause}
              ref={playButton}
              id="playButton"
              colorScheme="blue"
              w="120px"
            >
              <Kbd color="blue.600">Space</Kbd>&nbsp;Pause
            </Button>
          )}
        </WrapItem>
        <WrapItem visibility={selectedTime ? "visible" : "hidden"}>
          <Button
            disabled={!selectedTime}
            onClick={playSelection}
            colorScheme="blue"
          >
            <Kbd color="blue.600">,</Kbd>&nbsp;Play selection
          </Button>
        </WrapItem>
      </Wrap>
    </Skeleton>
  );
};

export default TopicPlayer;
