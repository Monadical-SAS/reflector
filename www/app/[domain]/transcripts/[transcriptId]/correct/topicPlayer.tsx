import { useEffect, useState } from "react";
import useMp3 from "../../useMp3";

const TopicPlayer = ({ transcriptId, selectedTime, topicTime }) => {
  const mp3 = useMp3(transcriptId);
  const [isPlaying, setIsPlaying] = useState(false);
  const [endTopicCallback, setEndTopicCallback] = useState<() => void>();
  const [endSelectionCallback, setEndSelectionCallback] =
    useState<() => void>();

  const keyHandler = (e) => {
    if (e.key == "!") {
      if (isPlaying) {
        mp3.media?.pause();
        setIsPlaying(false);
      } else {
        mp3.media?.play();
        setIsPlaying(true);
      }
    }
  };
  useEffect(() => {
    document.addEventListener("keyup", keyHandler);
    return () => {
      document.removeEventListener("keyup", keyHandler);
    };
  });

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
          }
        },
    );
    if (mp3.media && topicTime) {
      mp3.media?.pause();
      // there's no callback on pause but apparently changing the time while palying doesn't work... so here is a timeout
      setTimeout(() => {
        if (mp3.media) {
          mp3.media.currentTime = topicTime.start;
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

  const playSelection = () => {
    if (mp3.media && selectedTime?.start !== undefined) {
      mp3.media.currentTime = selectedTime.start;
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

  const playTopic = () => {
    if (mp3.media) {
      mp3.media.currentTime = topicTime.start;
      mp3.media.play();
      setIsPlaying(true);
      endSelectionCallback &&
        mp3.media.removeEventListener("timeupdate", endSelectionCallback);
    }
  };

  const playCurrent = () => {
    mp3.media?.play();
    setIsPlaying(true);
  };

  const pause = (e) => {
    mp3.media?.pause();
    setIsPlaying(false);
  };

  if (mp3.media) {
    return (
      <div id="audioContainer">
        {!isPlaying ? (
          <button onClick={playCurrent}>Play</button>
        ) : (
          <button onClick={pause}>Pause</button>
        )}
        {selectedTime && (
          <button onClick={playSelection}>Play Selection</button>
        )}
        {topicTime && <button onClick={playTopic}>Play Topic</button>}
      </div>
    );
  }
};

export default TopicPlayer;
