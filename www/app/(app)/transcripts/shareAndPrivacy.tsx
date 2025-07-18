import { useEffect, useState } from "react";
import { featureEnabled } from "../../domainContext";

import { ShareMode, toShareMode } from "../../lib/shareMode";
import { GetTranscript, GetTranscriptTopic, UpdateTranscript } from "../../api";
import { Box, Flex, IconButton, Text } from "@chakra-ui/react";

// Temporary Modal components until Chakra v3 Modal is properly imported
const Modal = ({ isOpen, onClose, children }: any) => {
  if (!isOpen) return null;
  return (
    <div
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: "rgba(0, 0, 0, 0.5)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1000,
      }}
      onClick={onClose}
    >
      <div onClick={(e) => e.stopPropagation()}>{children}</div>
    </div>
  );
};
const ModalOverlay = () => null;
const ModalContent = ({ children }: any) => (
  <div
    style={{
      backgroundColor: "white",
      borderRadius: "8px",
      maxWidth: "600px",
      width: "90%",
      maxHeight: "90vh",
      overflow: "auto",
    }}
  >
    {children}
  </div>
);
const ModalHeader = ({ children }: any) => (
  <div
    style={{
      padding: "20px",
      borderBottom: "1px solid #E2E8F0",
      fontSize: "20px",
      fontWeight: "bold",
    }}
  >
    {children}
  </div>
);
const ModalBody = ({ children }: any) => (
  <div style={{ padding: "20px" }}>{children}</div>
);
import { FaShare } from "react-icons/fa";
import useApi from "../../lib/useApi";
import useSessionUser from "../../lib/useSessionUser";
import { CustomSession } from "../../lib/types";
// import { Select } from "chakra-react-select";

// Temporary Select component
const Select = ({ options, value, onChange, disabled, loading }: any) => {
  return (
    <select
      value={value?.value || ""}
      onChange={(e) => {
        const selected = options.find(
          (opt: any) => opt.value === e.target.value,
        );
        onChange(selected);
      }}
      disabled={disabled || loading}
      style={{
        width: "100%",
        padding: "8px",
        borderRadius: "4px",
        border: "1px solid #E2E8F0",
        fontSize: "16px",
        backgroundColor: disabled || loading ? "#F7FAFC" : "white",
        cursor: disabled || loading ? "not-allowed" : "pointer",
        opacity: loading ? 0.6 : 1,
      }}
    >
      {options?.map((opt: any) => (
        <option key={opt.value} value={opt.value}>
          {opt.label}
        </option>
      ))}
    </select>
  );
};
import ShareLink from "./shareLink";
import ShareCopy from "./shareCopy";
import ShareZulip from "./shareZulip";

type ShareAndPrivacyProps = {
  finalSummaryRef: any;
  transcriptResponse: GetTranscript;
  topicsResponse: GetTranscriptTopic[];
};

type ShareOption = { value: ShareMode; label: string };

const shareOptions = [
  { label: "Private", value: toShareMode("private") },
  { label: "Secure", value: toShareMode("semi-private") },
  { label: "Public", value: toShareMode("public") },
];

export default function ShareAndPrivacy(props: ShareAndPrivacyProps) {
  const [showModal, setShowModal] = useState(false);
  const [isOwner, setIsOwner] = useState(false);
  const [shareMode, setShareMode] = useState<ShareOption>(
    shareOptions.find(
      (option) => option.value === props.transcriptResponse.share_mode,
    ) || shareOptions[0],
  );
  const [shareLoading, setShareLoading] = useState(false);
  const requireLogin = featureEnabled("requireLogin");
  const api = useApi();

  const updateShareMode = async (selectedShareMode: any) => {
    if (!api)
      throw new Error("ShareLink's API should always be ready at this point");

    setShareLoading(true);
    const requestBody: UpdateTranscript = {
      share_mode: toShareMode(selectedShareMode.value),
    };

    const updatedTranscript = await api.v1TranscriptUpdate({
      transcriptId: props.transcriptResponse.id,
      requestBody,
    });
    setShareMode(
      shareOptions.find(
        (option) => option.value === updatedTranscript.share_mode,
      ) || shareOptions[0],
    );
    setShareLoading(false);
  };

  const userId = useSessionUser().id;

  useEffect(() => {
    setIsOwner(!!(requireLogin && userId === props.transcriptResponse.user_id));
  }, [userId, props.transcriptResponse.user_id]);

  return (
    <>
      <IconButton
        icon={<FaShare />}
        onClick={() => setShowModal(true)}
        aria-label="Share"
      />
      <Modal open={!!showModal} onClose={() => setShowModal(false)} size={"xl"}>
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>Share</ModalHeader>
          <ModalBody>
            {requireLogin && (
              <Box mb={4}>
                <Text size="sm" mb="2" fontWeight={"bold"}>
                  Share mode
                </Text>
                <Text size="sm" mb="2">
                  {shareMode.value === "private" &&
                    "This transcript is private and can only be accessed by you."}
                  {shareMode.value === "semi-private" &&
                    "This transcript is secure. Only authenticated users can access it."}
                  {shareMode.value === "public" &&
                    "This transcript is public. Everyone can access it."}
                </Text>

                {isOwner && api && (
                  <Select
                    options={
                      [
                        { value: "private", label: "Private" },
                        { label: "Secure", value: "semi-private" },
                        { label: "Public", value: "public" },
                      ] as any
                    }
                    value={shareMode}
                    onChange={updateShareMode}
                    loading={shareLoading}
                  />
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
          </ModalBody>
        </ModalContent>
      </Modal>
    </>
  );
}
