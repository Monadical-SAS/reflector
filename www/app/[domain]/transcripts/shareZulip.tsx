import { useState } from "react";
import { featureEnabled } from "../domainContext";
import ShareModal from "./[transcriptId]/shareModal";
import { GetTranscript, GetTranscriptTopic } from "../../api";
import { Button } from "@chakra-ui/react";

type ShareZulipProps = {
  transcriptResponse: GetTranscript;
  topicsResponse: GetTranscriptTopic[];
};

export default function ShareZulip(props: ShareZulipProps) {
  const [showModal, setShowModal] = useState(false);
  if (!featureEnabled("sendToZulip")) return null;

  return (
    <>
      <Button colorScheme="blue" onClick={() => setShowModal(true)}>
        ➡️ Zulip
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
