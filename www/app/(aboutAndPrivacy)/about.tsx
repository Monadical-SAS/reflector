"use client";
import React, { useState } from "react";
import FullscreenModal from "../transcripts/fullsreenModal";
import AboutContent from "./aboutContent";

type AboutProps = {
  buttonText: string;
};

export default function About({ buttonText }: AboutProps) {
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
          <AboutContent />
        </FullscreenModal>
      )}
    </>
  );
}
