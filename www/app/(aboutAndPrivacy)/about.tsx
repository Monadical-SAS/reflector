"use client";
import React, { useState } from "react";
import FullscreenModal from "./fullsreenModal";
import AboutContent from "./aboutContent";
import { Button } from "@chakra-ui/react";

type AboutProps = {
  buttonText: string;
};

export default function About({ buttonText }: AboutProps) {
  const [modalOpen, setModalOpen] = useState(false);

  return (
    <>
      <Button mt={2} onClick={() => setModalOpen(true)} variant="subtle">
        {buttonText}
      </Button>
      {modalOpen && (
        <FullscreenModal close={() => setModalOpen(false)}>
          <AboutContent />
        </FullscreenModal>
      )}
    </>
  );
}
