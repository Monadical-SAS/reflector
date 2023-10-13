import React, { useState, useRef, useEffect, use } from "react";
import { featPrivacy } from "../lib/utils";

const ShareLink = () => {
  const [isCopied, setIsCopied] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const [currentUrl, setCurrentUrl] = useState<string>("");

  useEffect(() => {
    setCurrentUrl(window.location.href);
  }, []);

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

  return (
    <div
      className="p-2 md:p-4 rounded"
      style={{ background: "rgba(96, 165, 250, 0.2)" }}
    >
      {featPrivacy() ? (
        <p className="text-sm mb-2">
          You can share this link with others. Anyone with the link will have
          access to the page, including the full audio recording, for the next 7
          days.
        </p>
      ) : (
        <p className="text-sm mb-2">
          You can share this link with others. Anyone with the link will have
          access to the page, including the full audio recording.
        </p>
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
