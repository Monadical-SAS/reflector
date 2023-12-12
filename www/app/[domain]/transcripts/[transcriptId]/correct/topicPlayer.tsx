import { useEffect, useState } from "react";
import useMp3 from "../../useMp3";
import { formatTime } from "../../../../lib/time";
import SoundWaveCss from "./soundWaveCss";

const TopicPlayer = ({ transcriptId, selectedTime, topicTime }) => {
  const mp3 = useMp3(transcriptId);
  const [isPlaying, setIsPlaying] = useState(false);
  const [endTopicCallback, setEndTopicCallback] = useState<() => void>();
  const [endSelectionCallback, setEndSelectionCallback] =
    useState<() => void>();
  const [showTime, setShowTime] = useState("");

  const keyHandler = (e) => {
    if (e.key == " ") {
      if (isPlaying) {
        mp3.media?.pause();
        setIsPlaying(false);
      } else {
        mp3.media?.play();
        setIsPlaying(true);
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
            mp3.media &&
            topicTime.end &&
            mp3.media.currentTime >= topicTime.end
          ) {
            mp3.media.pause();
            setIsPlaying(false);
            mp3.media.currentTime = topicTime.start;
            calcShowTime();
          }
        },
    );
    if (mp3.media && topicTime) {
      mp3.media?.pause();
      // there's no callback on pause but apparently changing the time while palying doesn't work... so here is a timeout
      setTimeout(() => {
        if (mp3.media) {
          mp3.media.currentTime = topicTime.start;
          setShowTime(`00:00/${formatTime(topicTime.end - topicTime.start)}`);
        }
      }, 10);
      setIsPlaying(false);
    }
  }, [topicTime, mp3.media]);

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

  if (mp3.media) {
    return (
      <div className="mb-4 grid grid-cols-3 gap-2">
        <SoundWaveCss playing={isPlaying} />
        <div className="col-span-2">{showTime}</div>
        {topicTime && (
          <button className="p-2 bg-blue-200 w-full" onClick={playTopic}>
            Play From Start
          </button>
        )}
        {!isPlaying ? (
          <button className="p-2 bg-blue-200 w-full" onClick={playCurrent}>
            <span className="text-xs">[SPACE]</span> Play
          </button>
        ) : (
          <button className="p-2 bg-blue-200 w-full" onClick={pause}>
            <span className="text-xs">[SPACE]</span> Pause
          </button>
        )}
        {selectedTime && (
          <button className="p-2 bg-blue-200 w-full" onClick={playSelection}>
            <span className="text-xs">[,]</span>Play Selection
          </button>
        )}
      </div>
    );
  }
};

export default TopicPlayer;
