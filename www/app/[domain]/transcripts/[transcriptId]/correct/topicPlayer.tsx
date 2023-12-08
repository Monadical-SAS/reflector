import { useEffect, useState } from "react";
import useMp3 from "../../useMp3";

const TopicPlayer = ({ transcriptId, selectedTime, topicTime }) => {
  const mp3 = useMp3(transcriptId);
  const [isPlaying, setIsPlaying] = useState(false);
  const [endTopicCallback, setEndTopicCallback] = useState<() => void>();
  const [endSelectionCallback, setEndSelectionCallback] =
    useState<() => void>();

  //TODO shortcuts

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
    if (mp3.media) {
      mp3.media.currentTime = topicTime.start;
    }
  }, [topicTime]);

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

  const setEndTime = (time) => () => {
    if (mp3.media && time && mp3.media.currentTime >= time) {
      mp3.media.pause();
      setIsPlaying(false);
      mp3.media.removeEventListener("timeupdate", setEndTime);
    }
  };

  const playSelection = () => {
    if (mp3.media && selectedTime?.start !== undefined) {
      mp3.media.currentTime = selectedTime?.start;
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
              endSelectionCallback &&
                removeEventListener("timeupdate", endSelectionCallback);
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

  const pause = () => {
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
