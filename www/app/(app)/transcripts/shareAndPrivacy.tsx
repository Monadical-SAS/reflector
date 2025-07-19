import { useEffect, useState } from "react";
import { featureEnabled } from "../../domainContext";

import { ShareMode, toShareMode } from "../../lib/shareMode";
import { GetTranscript, GetTranscriptTopic, UpdateTranscript } from "../../api";
import {
  Box,
  Flex,
  IconButton,
  Text,
  Dialog,
  Portal,
  CloseButton,
  Select,
  createListCollection,
} from "@chakra-ui/react";
import { FaShare } from "react-icons/fa";
import useApi from "../../lib/useApi";
import useSessionUser from "../../lib/useSessionUser";
import { CustomSession } from "../../lib/types";
import ShareLink from "./shareLink";
import ShareCopy from "./shareCopy";
import ShareZulip from "./shareZulip";

type ShareAndPrivacyProps = {
  finalSummaryRef: any;
  transcriptResponse: GetTranscript;
  topicsResponse: GetTranscriptTopic[];
};

type ShareOption = { value: ShareMode; label: string };

const shareOptionsData = [
  { label: "Private", value: toShareMode("private") },
  { label: "Secure", value: toShareMode("semi-private") },
  { label: "Public", value: toShareMode("public") },
];

const shareOptions = createListCollection({
  items: shareOptionsData,
});

export default function ShareAndPrivacy(props: ShareAndPrivacyProps) {
  const [showModal, setShowModal] = useState(false);
  const [isOwner, setIsOwner] = useState(false);
  const [shareMode, setShareMode] = useState<ShareOption>(
    shareOptionsData.find(
      (option) => option.value === props.transcriptResponse.share_mode,
    ) || shareOptionsData[0],
  );
  const [shareLoading, setShareLoading] = useState(false);
  const requireLogin = featureEnabled("requireLogin");
  const api = useApi();

  const updateShareMode = async (selectedValue: string) => {
    if (!api)
      throw new Error("ShareLink's API should always be ready at this point");

    const selectedOption = shareOptionsData.find(
      (option) => option.value === selectedValue,
    );

    if (!selectedOption) return;

    setShareLoading(true);
    const requestBody: UpdateTranscript = {
      share_mode: selectedValue,
    };

    const updatedTranscript = await api.v1TranscriptUpdate({
      transcriptId: props.transcriptResponse.id,
      requestBody,
    });
    setShareMode(
      shareOptionsData.find(
        (option) => option.value === updatedTranscript.share_mode,
      ) || shareOptionsData[0],
    );
    setShareLoading(false);
  };

  const userId = useSessionUser().id;

  useEffect(() => {
    setIsOwner(!!(requireLogin && userId === props.transcriptResponse.user_id));
  }, [userId, props.transcriptResponse.user_id]);

  return (
    <>
      <IconButton onClick={() => setShowModal(true)} aria-label="Share">
        <FaShare />
      </IconButton>
      <Dialog.Root open={showModal} onOpenChange={setShowModal} size="lg">
        <Dialog.Backdrop />
        <Dialog.Positioner>
          <Dialog.Content>
            <Dialog.Header>
              <Dialog.Title>Share</Dialog.Title>
              <Dialog.CloseTrigger asChild>
                <CloseButton />
              </Dialog.CloseTrigger>
            </Dialog.Header>
            <Dialog.Body>
              {requireLogin && (
                <Box mb={4}>
                  <Text mb="2" fontWeight={"bold"}>
                    Share mode
                  </Text>
                  <Text mb="2">
                    {shareMode.value === "private" &&
                      "This transcript is private and can only be accessed by you."}
                    {shareMode.value === "semi-private" &&
                      "This transcript is secure. Only authenticated users can access it."}
                    {shareMode.value === "public" &&
                      "This transcript is public. Everyone can access it."}
                  </Text>

                  {isOwner && api && (
                    <Select.Root
                      key={shareMode.value}
                      value={shareMode.value}
                      onValueChange={(e) => updateShareMode(e.value[0])}
                      disabled={shareLoading}
                      collection={shareOptions}
                      lazyMount={true}
                    >
                      <Select.HiddenSelect />
                      <Select.Control>
                        <Select.Trigger>
                          <Select.ValueText>{shareMode.label}</Select.ValueText>
                        </Select.Trigger>
                        <Select.IndicatorGroup>
                          <Select.Indicator />
                        </Select.IndicatorGroup>
                      </Select.Control>
                      <Select.Positioner>
                        <Select.Content>
                          {shareOptions.items.map((option) => (
                            <Select.Item
                              key={option.value}
                              item={option}
                              label={option.label}
                            >
                              {option.label}
                              <Select.ItemIndicator />
                            </Select.Item>
                          ))}
                        </Select.Content>
                      </Select.Positioner>
                    </Select.Root>
                  )}
                </Box>
              )}

              <Text size="sm" mb="2" fontWeight={"bold"}>
                Share options
              </Text>
              <Flex gap={2} mb={2}>
                {requireLogin && (
                  <ShareZulip
                    transcriptResponse={props.transcriptResponse}
                    topicsResponse={props.topicsResponse}
                    disabled={toShareMode(shareMode.value) === "private"}
                  />
                )}
                <ShareCopy
                  finalSummaryRef={props.finalSummaryRef}
                  transcriptResponse={props.transcriptResponse}
                  topicsResponse={props.topicsResponse}
                />
              </Flex>

              <ShareLink transcriptId={props.transcriptResponse.id} />
            </Dialog.Body>
          </Dialog.Content>
        </Dialog.Positioner>
      </Dialog.Root>
    </>
  );
}
