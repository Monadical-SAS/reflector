import { useState, useEffect, useMemo } from "react";
import type { components } from "../../reflector-api";

type GetTranscriptWithParticipants =
  components["schemas"]["GetTranscriptWithParticipants"];
type GetTranscriptTopic = components["schemas"]["GetTranscriptTopic"];
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
  createListCollection,
} from "@chakra-ui/react";
import { TbBrandZulip } from "react-icons/tb";
import {
  useZulipStreams,
  useZulipTopics,
  useTranscriptPostToZulip,
} from "../../lib/apiHooks";

import { featureEnabled } from "../../lib/features";

type ShareZulipProps = {
  transcript: GetTranscriptWithParticipants;
  topics: GetTranscriptTopic[];
  disabled: boolean;
};

interface Stream {
  stream_id: number;
  name: string;
}

export default function ShareZulip(props: ShareZulipProps & BoxProps) {
  const [showModal, setShowModal] = useState(false);
  const [stream, setStream] = useState<string | undefined>(undefined);
  const [selectedStreamId, setSelectedStreamId] = useState<number | null>(null);
  const [topic, setTopic] = useState<string | undefined>(undefined);
  const [includeTopics, setIncludeTopics] = useState(false);

  const { data: streams = [], isLoading: isLoadingStreams } = useZulipStreams();
  const { data: topics = [] } = useZulipTopics(selectedStreamId);
  const postToZulipMutation = useTranscriptPostToZulip();

  const streamItems = useMemo(() => {
    return streams.map((stream: Stream) => ({
      label: stream.name,
      value: stream.name,
    }));
  }, [streams]);

  const topicItems = useMemo(() => {
    return topics.map(({ name }) => ({
      label: name,
      value: name,
    }));
  }, [topics]);

  const streamCollection = useMemo(
    () =>
      createListCollection({
        items: streamItems,
      }),
    [streamItems],
  );

  const topicCollection = useMemo(
    () =>
      createListCollection({
        items: topicItems,
      }),
    [topicItems],
  );

  // Update selected stream ID when stream changes
  useEffect(() => {
    if (stream && streams) {
      const selectedStream = streams.find((s: Stream) => s.name === stream);
      setSelectedStreamId(selectedStream ? selectedStream.stream_id : null);
    } else {
      setSelectedStreamId(null);
    }
  }, [stream, streams]);

  const handleSendToZulip = async () => {
    if (!props.transcript) return;

    if (stream && topic) {
      try {
        await postToZulipMutation.mutateAsync({
          params: {
            path: {
              transcript_id: props.transcript.id,
            },
            query: {
              stream,
              topic,
              include_topics: includeTopics,
            },
          },
        });
        setShowModal(false);
      } catch (error) {
        console.error("Error posting to Zulip:", error);
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
              {isLoadingStreams ? (
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
                        collection={streamCollection}
                        value={stream ? [stream] : []}
                        onValueChange={(e) => {
                          setTopic(undefined);
                          setStream(e.value[0]);
                        }}
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
                            {streamItems.map((item) => (
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
                          collection={topicCollection}
                          value={topic ? [topic] : []}
                          onValueChange={(e) => setTopic(e.value[0])}
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
                              {topicItems.map((item) => (
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
