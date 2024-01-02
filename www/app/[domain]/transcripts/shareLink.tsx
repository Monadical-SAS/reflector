import React, { useState, useRef, useEffect, use } from "react";
import { featureEnabled } from "../domainContext";
import { useFiefUserinfo } from "@fief/fief/nextjs/react";
import SelectSearch from "react-select-search";
import "react-select-search/style.css";
import "../../styles/button.css";
import "../../styles/form.scss";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faSpinner } from "@fortawesome/free-solid-svg-icons";
import { UpdateTranscript } from "../../api";
import { ShareMode, toShareMode } from "../../lib/shareMode";
import useApi from "../../lib/useApi";
type ShareLinkProps = {
  transcriptId: string;
  userId: string | null;
  shareMode: ShareMode;
};

const ShareLink = (props: ShareLinkProps) => {
  const [isCopied, setIsCopied] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const [currentUrl, setCurrentUrl] = useState<string>("");
  const requireLogin = featureEnabled("requireLogin");
  const [isOwner, setIsOwner] = useState(false);
  const [shareMode, setShareMode] = useState<ShareMode>(props.shareMode);
  const [shareLoading, setShareLoading] = useState(false);
  const userinfo = useFiefUserinfo();
  const api = useApi();

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
    if (!api)
      throw new Error("ShareLink's API should always be ready at this point");

    setShareLoading(true);
    const requestBody: UpdateTranscript = {
      share_mode: toShareMode(selectedShareMode),
    };

    const updatedTranscript = await api.v1TranscriptUpdate(
      props.transcriptId,
      requestBody,
    );
    setShareMode(toShareMode(updatedTranscript.share_mode));
    setShareLoading(false);
  };
  const privacyEnabled = featureEnabled("privacy");

  return (
    <div
      className="p-2 md:p-4 rounded"
      style={{ background: "rgba(96, 165, 250, 0.2)" }}
    >
      {requireLogin && (
        <div className="text-sm mb-2">
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
            <div className="relative">
              <SelectSearch
                className="select-search--top select-search"
                options={[
                  { name: "Private", value: "private" },
                  { name: "Secure", value: "semi-private" },
                  { name: "Public", value: "public" },
                ]}
                value={shareMode?.toString()}
                onChange={updateShareMode}
                closeOnSelect={true}
              />
              {shareLoading && (
                <div className="h-4 w-4 absolute top-1/3 right-3 z-10">
                  <FontAwesomeIcon
                    icon={faSpinner}
                    className="animate-spin-slow text-gray-600 flex-grow rounded-lg md:rounded-xl h-4 w-4"
                  />
                </div>
              )}
            </div>
          )}
        </div>
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
