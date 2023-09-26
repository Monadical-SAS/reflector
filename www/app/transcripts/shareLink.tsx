import React, { useState, useRef } from "react";

const ShareLink = () => {
  const [isCopied, setIsCopied] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const currentURL = window.location.href;

  const handleCopyClick = () => {
    if (inputRef.current) {
      inputRef.current.select();
      document.execCommand("copy");
      setIsCopied(true);

      // Reset the copied state after 2 seconds
      setTimeout(() => setIsCopied(false), 2000);
    }
  };

  return (
    <div
      className="p-2 md:p-4 mt-8 md:mt-4 rounded"
      style={{ background: "rgba(96, 165, 250, 0.2)" }}
    >
      <p className="text-sm mb-2">
        You can share this link with others. Anyone with the link will have
        access to the page, including the full audio recording, for the next 7
        days.
      </p>
      <div className="flex items-center">
        <input
          type="text"
          readOnly
          value={currentURL}
          ref={inputRef}
          className="border rounded p-2 flex-grow mr-2 text-sm bg-slate-100 outline-slate-400"
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
