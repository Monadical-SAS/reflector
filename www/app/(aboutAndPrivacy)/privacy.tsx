"use client";
import React, { useState } from "react";
import FullscreenModal from "./fullsreenModal";
import PrivacyContent from "./privacyContent";
import { Button } from "@chakra-ui/react";

type PrivacyProps = {
  buttonText: string;
};

export default function Privacy({ buttonText }: PrivacyProps) {
  const [modalOpen, setModalOpen] = useState(false);

  return (
    <>
      <Button mt={2} onClick={() => setModalOpen(true)}>
        {buttonText}
      </Button>
      {modalOpen && (
        <FullscreenModal close={() => setModalOpen(false)}>
          <PrivacyContent />
        </FullscreenModal>
      )}
    </>
  );
}
