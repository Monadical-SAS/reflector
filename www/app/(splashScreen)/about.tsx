"use client";
import React, { useState } from "react";
import FullscreenModal from "./fullsreenModal";
import AboutContent from "./aboutContent";

type AboutProps = {
  buttonText: string;
};

export default function About({ buttonText }: AboutProps) {
  const [modalOpen, setModalOpen] = useState(false);

  return (
    <>
      <button className="open-modal-button" onClick={() => setModalOpen(true)}>
        {buttonText}
      </button>
      {modalOpen && (
        <FullscreenModal close={() => setModalOpen(false)}>
          <AboutContent />
        </FullscreenModal>
      )}
    </>
  );
}
