import { useState, useEffect } from "react";
import { featureEnabled } from "../../domainContext";
import { GetTranscript, GetTranscriptTopic } from "../../api";
import {
  BoxProps,
  Button,
  Dialog,
  CloseButton,
  Text,
  Box,
  Flex,
  Checkbox,
  Select,
  createListCollection,
  Spinner,
} from "@chakra-ui/react";
import useApi from "../../lib/useApi";

type ShareZulipProps = {
  transcriptResponse: GetTranscript;
  topicsResponse: GetTranscriptTopic[];
  disabled: boolean;
};

interface Stream {
  stream_id: number;
  name: string;
}

interface Topic {
  name: string;
}

export default function ShareZulip(props: ShareZulipProps & BoxProps) {
  const [showModal, setShowModal] = useState(false);
  const [stream, setStream] = useState<string | undefined>(undefined);
  const [topic, setTopic] = useState<string | undefined>(undefined);
  const [includeTopics, setIncludeTopics] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [streams, setStreams] = useState<Stream[]>([]);
  const [topics, setTopics] = useState<Topic[]>([]);
  const api = useApi();

  useEffect(() => {
    const fetchZulipStreams = async () => {
      if (!api) return;

      try {
        const response = await api.v1ZulipGetStreams();
        setStreams(response);
        setIsLoading(false);
      } catch (error) {
        console.error("Error fetching Zulip streams:", error);
      }
    };

    fetchZulipStreams();
  }, [!api]);

  useEffect(() => {
    const fetchZulipTopics = async () => {
      if (!api || !stream) return;
      try {
        const selectedStream = streams.find((s) => s.name === stream);
        if (selectedStream) {
          const response = await api.v1ZulipGetTopics({
            streamId: selectedStream.stream_id,
          });
          setTopics(response);
        }
      } catch (error) {
        console.error("Error fetching Zulip topics:", error);
      }
    };

    fetchZulipTopics();
  }, [stream, streams, api]);

  const handleSendToZulip = async () => {
    if (!api || !props.transcriptResponse) return;

    if (stream && topic) {
      try {
        await api.v1TranscriptPostToZulip({
          transcriptId: props.transcriptResponse.id,
          stream,
          topic,
          includeTopics,
        });
        setShowModal(false);
      } catch (error) {
        console.log(error);
      }
    }
  };

  if (!featureEnabled("sendToZulip")) return null;

  const streamOptions = createListCollection({
    items: streams.map((stream) => ({
      label: stream.name,
      value: stream.name,
    })),
  });

  const topicOptions = createListCollection({
    items: topics.map((topic) => ({
      label: topic.name,
      value: topic.name,
    })),
  });

  return (
    <>
      <Button
        colorPalette="blue"
        size={"sm"}
        disabled={props.disabled}
        onClick={() => setShowModal(true)}
      >
        ➡️ Send to Zulip
      </Button>

      <Dialog.Root
        open={showModal}
        onOpenChange={(e) => setShowModal(e.open)}
        size="md"
      >
        <Dialog.Backdrop />
        <Dialog.Positioner>
          <Dialog.Content>
            <Dialog.Header>
              <Dialog.Title>Send to Zulip</Dialog.Title>
              <Dialog.CloseTrigger asChild>
                <CloseButton />
              </Dialog.CloseTrigger>
            </Dialog.Header>
            <Dialog.Body>
              {isLoading ? (
                <Flex justify="center" py={8}>
                  <Spinner />
                </Flex>
              ) : (
                <>
                  <Box mb={4}>
                    <Checkbox.Root
                      checked={includeTopics}
                      onCheckedChange={(e) => setIncludeTopics(!!e.checked)}
                    >
                      <Checkbox.HiddenInput />
                      <Checkbox.Control>
                        <Checkbox.Indicator />
                      </Checkbox.Control>
                      <Checkbox.Label>Include topics</Checkbox.Label>
                    </Checkbox.Root>
                  </Box>

                  <Box mb={4}>
                    <Flex align="center" gap={2}>
                      <Text>#</Text>
                      <Select.Root
                        value={stream ? [stream] : []}
                        onValueChange={(e) => {
                          setTopic(undefined);
                          setStream(e.value[0]);
                        }}
                        collection={streamOptions}
                      >
                        <Select.HiddenSelect />
                        <Select.Control>
                          <Select.Trigger>
                            <Select.ValueText placeholder="Pick a stream" />
                          </Select.Trigger>
                          <Select.IndicatorGroup>
                            <Select.Indicator />
                          </Select.IndicatorGroup>
                        </Select.Control>
                        <Select.Positioner>
                          <Select.Content>
                            {streamOptions.items.map((option) => (
                              <Select.Item key={option.value} item={option}>
                                {option.label}
                                <Select.ItemIndicator />
                              </Select.Item>
                            ))}
                          </Select.Content>
                        </Select.Positioner>
                      </Select.Root>
                    </Flex>
                  </Box>

                  {stream && (
                    <Box mb={4}>
                      <Flex align="center" gap={2}>
                        <Text visibility="hidden">#</Text>
                        <Select.Root
                          value={topic ? [topic] : []}
                          onValueChange={(e) => setTopic(e.value[0])}
                          collection={topicOptions}
                        >
                          <Select.HiddenSelect />
                          <Select.Control>
                            <Select.Trigger>
                              <Select.ValueText placeholder="Pick a topic" />
                            </Select.Trigger>
                            <Select.IndicatorGroup>
                              <Select.Indicator />
                            </Select.IndicatorGroup>
                          </Select.Control>
                          <Select.Positioner>
                            <Select.Content>
                              {topicOptions.items.map((option) => (
                                <Select.Item key={option.value} item={option}>
                                  {option.label}
                                  <Select.ItemIndicator />
                                </Select.Item>
                              ))}
                            </Select.Content>
                          </Select.Positioner>
                        </Select.Root>
                      </Flex>
                    </Box>
                  )}
                </>
              )}
            </Dialog.Body>
            <Dialog.Footer>
              <Button
                colorPalette="blue"
                disabled={!stream || !topic}
                onClick={handleSendToZulip}
              >
                Send to Zulip
              </Button>
              <Button variant="ghost" onClick={() => setShowModal(false)}>
                Close
              </Button>
            </Dialog.Footer>
          </Dialog.Content>
        </Dialog.Positioner>
      </Dialog.Root>
    </>
  );
}
