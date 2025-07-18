import { useState } from "react";
import { featureEnabled } from "../../domainContext";
import ShareModal from "./[transcriptId]/shareModal";
import { GetTranscript, GetTranscriptTopic } from "../../api";
import { BoxProps, Button } from "@chakra-ui/react";

type ShareZulipProps = {
  transcriptResponse: GetTranscript;
  topicsResponse: GetTranscriptTopic[];
  disabled: boolean;
};

export default function ShareZulip(props: ShareZulipProps & BoxProps) {
  const [showModal, setShowModal] = useState(false);
  if (!featureEnabled("sendToZulip")) return null;

  return (
    <>
      <Button
        colorPalette="blue"
        size={"sm"}
        isDisabled={props.disabled}
        onClick={() => setShowModal(true)}
      >
        ➡️ Send to Zulip
      </Button>

      <ShareModal
        transcript={props.transcriptResponse}
        topics={props.topicsResponse}
        show={showModal}
        setShow={(v) => setShowModal(v)}
      />
    </>
  );
}
