import useTopics from "../../useTopics";
import { Dispatch, SetStateAction, useEffect } from "react";
import type { components } from "../../../../reflector-api";
type GetTranscriptTopic = components["schemas"]["GetTranscriptTopic"];
import {
  BoxProps,
  Box,
  Circle,
  Heading,
  Kbd,
  Skeleton,
  SkeletonCircle,
  Flex,
} from "@chakra-ui/react";
import { ChevronLeft, ChevronRight } from "lucide-react";

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
      {isLoaded ? (
        <Circle
          as="button"
          onClick={canGoPrevious ? onPrev : undefined}
          size="40px"
          border="1px"
          color={canGoPrevious ? "inherit" : "gray"}
          borderColor={canGoNext ? "body-text" : "gray"}
          cursor={canGoPrevious ? "pointer" : "not-allowed"}
          opacity={canGoPrevious ? 1 : 0.5}
        >
          {canGoPrevious ? (
            <Kbd>
              <ChevronLeft size={16} />
            </Kbd>
          ) : (
            <ChevronLeft size={16} />
          )}
        </Circle>
      ) : (
        <SkeletonCircle h="40px" w="40px" mb="2" />
      )}
      {isLoaded ? (
        <Flex wrap="nowrap" justifyContent="center" flexGrow={1} mx={6}>
          <Heading size="lg" textAlign="center" lineClamp={1}>
            {currentTopic?.title}{" "}
          </Heading>
          <Heading size="lg" ml="3">
            {(number || 0) + 1}/{total}
          </Heading>
        </Flex>
      ) : (
        <Skeleton h="40px" mb="2" flexGrow={1} mx={6} />
      )}
      {isLoaded ? (
        <Circle
          as="button"
          onClick={canGoNext ? onNext : undefined}
          size="40px"
          border="1px"
          color={canGoNext ? "inherit" : "gray"}
          borderColor={canGoNext ? "body-text" : "gray"}
          cursor={canGoNext ? "pointer" : "not-allowed"}
          opacity={canGoNext ? 1 : 0.5}
        >
          {canGoNext ? (
            <Kbd>
              <ChevronRight size={16} />
            </Kbd>
          ) : (
            <ChevronRight size={16} />
          )}
        </Circle>
      ) : (
        <SkeletonCircle h="40px" w="40px" mb="2" />
      )}
    </Box>
  );
}
