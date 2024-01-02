import useTopics from "../../useTopics";
import { Dispatch, SetStateAction, useEffect } from "react";
import { GetTranscriptTopic } from "../../../../api";
import {
  BoxProps,
  Box,
  Circle,
  Heading,
  Kbd,
  Skeleton,
  SkeletonCircle,
  chakra,
  Flex,
  Center,
} from "@chakra-ui/react";
import { ChevronLeftIcon, ChevronRightIcon } from "@chakra-ui/icons";

type TopicHeader = {
  stateCurrentTopic: [
    GetTranscriptTopic | undefined,
    Dispatch<SetStateAction<GetTranscriptTopic | undefined>>,
  ];
  transcriptId: string;
  topicWithWordsLoading: boolean;
};

export default function TopicHeader({
  stateCurrentTopic,
  transcriptId,
  topicWithWordsLoading,
  ...chakraProps
}: TopicHeader & BoxProps) {
  const [currentTopic, setCurrentTopic] = stateCurrentTopic;
  const topics = useTopics(transcriptId);

  useEffect(() => {
    if (!topics.loading && !currentTopic) {
      const sessionTopic = window.localStorage.getItem(
        transcriptId + "correct",
      );
      if (sessionTopic && topics?.topics?.find((t) => t.id == sessionTopic)) {
        setCurrentTopic(topics?.topics?.find((t) => t.id == sessionTopic));
      } else {
        setCurrentTopic(topics?.topics?.at(0));
      }
    }
  }, [topics.loading]);

  const number = topics.topics?.findIndex(
    (topic) => topic.id == currentTopic?.id,
  );
  const canGoPrevious = typeof number == "number" && number > 0;
  const total = topics.topics?.length;
  const canGoNext = total && typeof number == "number" && number + 1 < total;

  const onPrev = () => {
    if (topicWithWordsLoading) return;
    canGoPrevious && setCurrentTopic(topics.topics?.at(number - 1));
  };
  const onNext = () => {
    if (topicWithWordsLoading) return;
    canGoNext && setCurrentTopic(topics.topics?.at(number + 1));
  };

  useEffect(() => {
    console.log(currentTopic?.id);

    currentTopic?.id &&
      window.localStorage.setItem(transcriptId + "correct", currentTopic?.id);
  }, [currentTopic?.id]);

  const keyHandler = (e) => {
    if (e.key == "ArrowLeft") {
      onPrev();
    } else if (e.key == "ArrowRight") {
      onNext();
    }
  };
  useEffect(() => {
    document.addEventListener("keyup", keyHandler);
    return () => {
      document.removeEventListener("keyup", keyHandler);
    };
  });

  const isLoaded = !!(
    topics.topics &&
    currentTopic &&
    typeof number == "number"
  );
  return (
    <Box
      display="flex"
      w="100%"
      justifyContent="space-between"
      {...chakraProps}
    >
      <SkeletonCircle
        isLoaded={isLoaded}
        h={isLoaded ? "auto" : "40px"}
        w={isLoaded ? "auto" : "40px"}
        mb="2"
        fadeDuration={1}
      >
        <Circle
          as="button"
          onClick={onPrev}
          disabled={!canGoPrevious}
          size="40px"
          border="1px"
          color={canGoPrevious ? "inherit" : "gray"}
          borderColor={canGoNext ? "body-text" : "gray"}
        >
          {canGoPrevious ? (
            <Kbd>
              <ChevronLeftIcon />
            </Kbd>
          ) : (
            <ChevronLeftIcon />
          )}
        </Circle>
      </SkeletonCircle>
      <Skeleton
        isLoaded={isLoaded}
        h={isLoaded ? "auto" : "40px"}
        mb="2"
        fadeDuration={1}
        flexGrow={1}
        mx={6}
      >
        <Flex wrap="nowrap" justifyContent="center">
          <Heading size="lg" textAlign="center" noOfLines={1}>
            {currentTopic?.title}{" "}
          </Heading>
          <Heading size="lg" ml="3">
            {(number || 0) + 1}/{total}
          </Heading>
        </Flex>
      </Skeleton>
      <SkeletonCircle
        isLoaded={isLoaded}
        h={isLoaded ? "auto" : "40px"}
        w={isLoaded ? "auto" : "40px"}
        mb="2"
        fadeDuration={1}
      >
        <Circle
          as="button"
          onClick={onNext}
          disabled={!canGoNext}
          size="40px"
          border="1px"
          color={canGoNext ? "inherit" : "gray"}
          borderColor={canGoNext ? "body-text" : "gray"}
        >
          {canGoNext ? (
            <Kbd>
              <ChevronRightIcon />
            </Kbd>
          ) : (
            <ChevronRightIcon />
          )}
        </Circle>
      </SkeletonCircle>
    </Box>
  );
}
