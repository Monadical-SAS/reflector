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
      <button
        className="inline-flex items-start justify-start text-left hover:no-underline underline underline-offset-2 decoration-[.5px] font-light pl-0 text-white text-[15px] font-poppins font-normal leading-normal"
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
