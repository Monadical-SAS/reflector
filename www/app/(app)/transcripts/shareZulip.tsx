import { useState, useEffect, useMemo } from "react";
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
  Combobox,
  Spinner,
  Portal,
  useFilter,
  useListCollection,
} from "@chakra-ui/react";
import { TbBrandZulip } from "react-icons/tb";
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
  const { contains } = useFilter({ sensitivity: "base" });

  const {
    collection: streamItemsCollection,
    filter: streamItemsFilter,
    set: streamItemsSet,
  } = useListCollection({
    items: [],
    filter: contains,
  });

  const {
    collection: topicItemsCollection,
    filter: topicItemsFilter,
    set: topicItemsSet,
  } = useListCollection({
    items: [],
    filter: contains,
  });

  useEffect(() => {
    const fetchZulipStreams = async () => {
      if (!api) return;

      try {
        const response = await api.v1ZulipGetStreams();
        setStreams(response);

        streamItemsSet(
          response.map((stream) => ({
            label: stream.name,
            value: stream.name,
          })),
        );

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
          topicItemsSet(
            response.map((topic) => ({
              label: topic.name,
              value: topic.name,
            })),
          );
        } else {
          topicItemsSet([]);
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

  return (
    <>
      <Button disabled={props.disabled} onClick={() => setShowModal(true)}>
        <TbBrandZulip /> Send to Zulip
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
                      <Combobox.Root
                        collection={streamItemsCollection}
                        value={stream ? [stream] : []}
                        onValueChange={(e) => {
                          setTopic(undefined);
                          setStream(e.value[0]);
                        }}
                        onInputValueChange={(e) =>
                          streamItemsFilter(e.inputValue)
                        }
                        openOnClick={true}
                        positioning={{
                          strategy: "fixed",
                          hideWhenDetached: true,
                        }}
                      >
                        <Combobox.Control>
                          <Combobox.Input placeholder="Pick a stream" />
                          <Combobox.IndicatorGroup>
                            <Combobox.ClearTrigger />
                            <Combobox.Trigger />
                          </Combobox.IndicatorGroup>
                        </Combobox.Control>
                        <Combobox.Positioner>
                          <Combobox.Content>
                            <Combobox.Empty>No streams found</Combobox.Empty>
                            {streamItemsCollection.items.map((item) => (
                              <Combobox.Item key={item.value} item={item}>
                                {item.label}
                              </Combobox.Item>
                            ))}
                          </Combobox.Content>
                        </Combobox.Positioner>
                      </Combobox.Root>
                    </Flex>
                  </Box>

                  {stream && (
                    <Box mb={4}>
                      <Flex align="center" gap={2}>
                        <Text visibility="hidden">#</Text>
                        <Combobox.Root
                          collection={topicItemsCollection}
                          value={topic ? [topic] : []}
                          onValueChange={(e) => setTopic(e.value[0])}
                          onInputValueChange={(e) =>
                            topicItemsFilter(e.inputValue)
                          }
                          openOnClick
                          selectionBehavior="replace"
                          skipAnimationOnMount={true}
                          closeOnSelect={true}
                          positioning={{
                            strategy: "fixed",
                            hideWhenDetached: true,
                          }}
                        >
                          <Combobox.Control>
                            <Combobox.Input placeholder="Pick a topic" />
                            <Combobox.IndicatorGroup>
                              <Combobox.ClearTrigger />
                              <Combobox.Trigger />
                            </Combobox.IndicatorGroup>
                          </Combobox.Control>
                          <Combobox.Positioner>
                            <Combobox.Content>
                              <Combobox.Empty>No topics found</Combobox.Empty>
                              {topicItemsCollection.items.map((item) => (
                                <Combobox.Item key={item.value} item={item}>
                                  {item.label}
                                  <Combobox.ItemIndicator />
                                </Combobox.Item>
                              ))}
                            </Combobox.Content>
                          </Combobox.Positioner>
                        </Combobox.Root>
                      </Flex>
                    </Box>
                  )}
                </>
              )}
            </Dialog.Body>
            <Dialog.Footer>
              <Button variant="ghost" onClick={() => setShowModal(false)}>
                Close
              </Button>
              <Button disabled={!stream || !topic} onClick={handleSendToZulip}>
                Send to Zulip
              </Button>
            </Dialog.Footer>
          </Dialog.Content>
        </Dialog.Positioner>
      </Dialog.Root>
    </>
  );
}
