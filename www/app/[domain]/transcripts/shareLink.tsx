import React, { useState, useRef, useEffect, use } from "react";
import { featureEnabled } from "../domainContext";
import getApi from "../../lib/getApi";
import { useFiefUserinfo } from "@fief/fief/nextjs/react";
import SelectSearch from "react-select-search";
import "react-select-search/style.css";
import "../../styles/button.css";
import "../../styles/form.scss";

type ShareLinkProps = {
  protectedPath: boolean;
  transcriptId: string;
  userId: string | null;
  shareMode: string;
};

const ShareLink = (props: ShareLinkProps) => {
  const [isCopied, setIsCopied] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const [currentUrl, setCurrentUrl] = useState<string>("");
  const requireLogin = featureEnabled("requireLogin");
  const [isOwner, setIsOwner] = useState(false);
  const [shareMode, setShareMode] = useState(props.shareMode);
  const api = getApi(props.protectedPath);
  const userinfo = useFiefUserinfo();

  useEffect(() => {
    setCurrentUrl(window.location.href);
  }, []);

  useEffect(() => {
    setIsOwner(!!(requireLogin && userinfo?.sub === props.userId));
  }, [userinfo, props.userId]);

  const handleCopyClick = () => {
    if (inputRef.current) {
      let text_to_copy = inputRef.current.value;

      text_to_copy &&
        navigator.clipboard.writeText(text_to_copy).then(() => {
          setIsCopied(true);
          // Reset the copied state after 2 seconds
          setTimeout(() => setIsCopied(false), 2000);
        });
    }
  };

  const updateShareMode = async (selectedShareMode: string) => {
    if (!api) return;
    const updatedTranscript = await api.v1TranscriptUpdate({
      transcriptId: props.transcriptId,
      updateTranscript: {
        shareMode: selectedShareMode,
      },
    });
    setShareMode(updatedTranscript.shareMode);
  };
  const privacyEnabled = featureEnabled("privacy");

  return (
    <div
      className="p-2 md:p-4 rounded"
      style={{ background: "rgba(96, 165, 250, 0.2)" }}
    >
      {requireLogin && (
        <p className="text-sm mb-2">
          {shareMode === "private" && (
            <p>This transcript is private and can only be accessed by you.</p>
          )}
          {shareMode === "semi-private" && (
            <p>
              This transcript is secure. Only authenticated users can access it.
            </p>
          )}
          {shareMode === "public" && (
            <p>This transcript is public. Everyone can access it.</p>
          )}

          {isOwner && api && (
            <p>
              <SelectSearch
                className="select-search--top select-search"
                options={[
                  { name: "Private", value: "private" },
                  { name: "Secure", value: "semi-private" },
                  { name: "Public", value: "public" },
                ]}
                value={shareMode}
                onChange={updateShareMode}
              />
            </p>
          )}
        </p>
      )}
      {!requireLogin && (
        <>
          {privacyEnabled ? (
            <p className="text-sm mb-2">
              Share this link to grant others access to this page. The link
              includes the full audio recording and is valid for the next 7
              days.
            </p>
          ) : (
            <p className="text-sm mb-2">
              Share this link to allow others to view this page and listen to
              the full audio recording.
            </p>
          )}
        </>
      )}
      <div className="flex items-center">
        <input
          type="text"
          readOnly
          value={currentUrl}
          ref={inputRef}
          onChange={() => {}}
          className="border rounded-lg md:rounded-xl p-2 flex-grow flex-shrink overflow-auto mr-2 text-sm bg-slate-100 outline-slate-400"
        />
        <button
          onClick={handleCopyClick}
          className={
            (isCopied ? "bg-blue-500" : "bg-blue-400") +
            " hover:bg-blue-500 focus-visible:bg-blue-500 text-white rounded p-2"
          }
          style={{ minHeight: "38px" }}
        >
          {isCopied ? "Copied!" : "Copy"}
        </button>
      </div>
    </div>
  );
};

export default ShareLink;
