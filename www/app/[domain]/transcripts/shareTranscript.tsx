import { useState } from "react";
import { featureEnabled } from "../domainContext";
import ShareModal from "./[transcriptId]/shareModal";
import ShareLink from "./shareLink";
import QRCode from "react-qr-code";
import { toShareMode } from "../../lib/shareMode";
import { GetTranscript, GetTranscriptTopic } from "../../api";

type ShareTranscriptProps = {
  finalSummaryRef: any;
  transcriptResponse: GetTranscript;
  topicsResponse: GetTranscriptTopic[];
};

export default function ShareTranscript(props: ShareTranscriptProps) {
  const [showModal, setShowModal] = useState(false);
  const [isCopiedSummary, setIsCopiedSummary] = useState(false);
  const [isCopiedTranscript, setIsCopiedTranscript] = useState(false);

  const onCopySummaryClick = () => {
    let text_to_copy = props.finalSummaryRef.current?.innerText;

    text_to_copy &&
      navigator.clipboard.writeText(text_to_copy).then(() => {
        setIsCopiedSummary(true);
        // Reset the copied state after 2 seconds
        setTimeout(() => setIsCopiedSummary(false), 2000);
      });
  };

  const onCopyTranscriptClick = () => {
    let text_to_copy =
      props.topicsResponse
        ?.map((topic) => topic.transcript)
        .join("\n\n")
        .replace(/ +/g, " ")
        .trim() || "";

    text_to_copy &&
      navigator.clipboard.writeText(text_to_copy).then(() => {
        setIsCopiedTranscript(true);
        // Reset the copied state after 2 seconds
        setTimeout(() => setIsCopiedTranscript(false), 2000);
      });
  };

  return (
    <div>
      <>
        {featureEnabled("sendToZulip") && (
          <button
            className={
              "bg-blue-400 hover:bg-blue-500 focus-visible:bg-blue-500 text-white rounded p-2 sm:text-base"
            }
            onClick={() => setShowModal(true)}
          >
            <span className="text-xs">➡️ Zulip</span>
          </button>
        )}

        <button
          onClick={onCopyTranscriptClick}
          className={
            (isCopiedTranscript ? "bg-blue-500" : "bg-blue-400") +
            " hover:bg-blue-500 focus-visible:bg-blue-500 text-white rounded p-2 sm:text-base"
          }
          style={{ minHeight: "30px" }}
        >
          <span className="text-xs">
            {isCopiedTranscript ? "Copied!" : "Copy Transcript"}
          </span>
        </button>
        <button
          onClick={onCopySummaryClick}
          className={
            (isCopiedSummary ? "bg-blue-500" : "bg-blue-400") +
            " hover:bg-blue-500 focus-visible:bg-blue-500 text-white rounded p-2 sm:text-base"
          }
          style={{ minHeight: "30px" }}
        >
          <span className="text-xs">
            {isCopiedSummary ? "Copied!" : "Copy Summary"}
          </span>
        </button>
        {featureEnabled("sendToZulip") && (
          <ShareModal
            transcript={props.transcriptResponse}
            topics={props.topicsResponse}
            show={showModal}
            setShow={(v) => setShowModal(v)}
          />
        )}

        <QRCode
          value={`${location.origin}/transcripts/${props.transcriptResponse.id}`}
          level="L"
          size={98}
        />

        <ShareLink
          transcriptId={props.transcriptResponse.id}
          transcriptUserId={props.transcriptResponse.user_id}
          shareMode={toShareMode(props.transcriptResponse.share_mode)}
        />
      </>
    </div>
  );
}
