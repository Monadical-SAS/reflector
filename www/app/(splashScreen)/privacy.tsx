"use client";
import React, { useState } from "react";
import FullscreenModal from "./fullsreenModal";
import PrivacyContent from "./privacyContent";

type PrivacyProps = {
  buttonText: string;
};

export default function Privacy({ buttonText }: PrivacyProps) {
  const [modalOpen, setModalOpen] = useState(false);

  return (
    <>
      <button className="open-modal-button" onClick={() => setModalOpen(true)}>
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
