import { useEffect, useState } from "react";

import { ShareMode, toShareMode } from "../../lib/shareMode";
import type { components } from "../../reflector-api";
type GetTranscript = components["schemas"]["GetTranscript"];
type GetTranscriptTopic = components["schemas"]["GetTranscriptTopic"];
type UpdateTranscript = components["schemas"]["UpdateTranscript"];
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
import { LuShare2 } from "react-icons/lu";
import { useTranscriptUpdate } from "../../lib/apiHooks";
import ShareLink from "./shareLink";
import ShareCopy from "./shareCopy";
import ShareZulip from "./shareZulip";
import { useAuth } from "../../lib/AuthProvider";

import { featureEnabled } from "../../lib/config";

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
  const updateTranscriptMutation = useTranscriptUpdate();

  const updateShareMode = async (selectedValue: string) => {
    const selectedOption = shareOptionsData.find(
      (option) => option.value === selectedValue,
    );

    if (!selectedOption) return;

    setShareLoading(true);
    const requestBody: UpdateTranscript = {
      share_mode: selectedValue as "public" | "semi-private" | "private",
    };

    try {
      const updatedTranscript = await updateTranscriptMutation.mutateAsync({
        params: {
          path: { transcript_id: props.transcriptResponse.id },
        },
        body: requestBody,
      });
      setShareMode(
        shareOptionsData.find(
          (option) => option.value === updatedTranscript.share_mode,
        ) || shareOptionsData[0],
      );
    } catch (err) {
      console.error("Failed to update share mode:", err);
    } finally {
      setShareLoading(false);
    }
  };

  const auth = useAuth();
  const userId = auth.status === "authenticated" ? auth.user?.id : null;

  useEffect(() => {
    setIsOwner(!!(requireLogin && userId === props.transcriptResponse.user_id));
  }, [userId, props.transcriptResponse.user_id]);

  return (
    <>
      <IconButton
        onClick={() => setShowModal(true)}
        aria-label="Share"
        size="sm"
        variant="subtle"
      >
        <LuShare2 />
      </IconButton>
      <Dialog.Root
        open={showModal}
        onOpenChange={(e) => setShowModal(e.open)}
        size="lg"
      >
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

                  {isOwner && (
                    <Select.Root
                      key={shareMode.value}
                      value={[shareMode.value || ""]}
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
                            <Select.Item key={option.value} item={option}>
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

              <Text fontSize="sm" mb="2" fontWeight={"bold"}>
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
