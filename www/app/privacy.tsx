"use client";
import React, { useState } from "react";
import FullscreenModal from "./transcripts/fullsreenModal";
import PrivacyContent from "./privacyContent";

type PrivacyProps = {
  buttonText: string;
};

export default function Privacy({ buttonText }: PrivacyProps) {
  const [modalOpen, setModalOpen] = useState(false);

  return (
    <>
      <button
        className="hover:underline focus-within:underline underline-offset-2 decoration-[.5px] font-light px-2"
        onClick={() => setModalOpen(true)}
      >
        {buttonText}
      </button>
      {modalOpen && (
        <FullscreenModal close={() => setModalOpen(false)}>
          <PrivacyContent />
        </FullscreenModal>
      )}
    </>
  );
}
