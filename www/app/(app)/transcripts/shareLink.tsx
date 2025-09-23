import React, { useState, useRef, useEffect, use } from "react";
import { Button, Flex, Input, Text } from "@chakra-ui/react";
import QRCode from "react-qr-code";
import { featureEnabled } from "../../lib/features";

type ShareLinkProps = {
  transcriptId: string;
};

const ShareLink = (props: ShareLinkProps) => {
  const [isCopied, setIsCopied] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const [currentUrl, setCurrentUrl] = useState<string>("");
  const requireLogin = featureEnabled("requireLogin");
  const privacyEnabled = featureEnabled("privacy");

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
    <>
      {!requireLogin && (
        <>
          {privacyEnabled ? (
            <Text>
              Share this link to grant others access to this page. The link
              includes the full audio recording and is valid for the next 7
              days.
            </Text>
          ) : (
            <Text>
              Share this link to allow others to view this page and listen to
              the full audio recording.
            </Text>
          )}
        </>
      )}
      <Flex align={"center"}>
        <QRCode
          value={`${location.origin}/transcripts/${props.transcriptId}`}
          level="L"
          size={98}
        />
        <Input
          type="text"
          readOnly
          value={currentUrl}
          ref={inputRef}
          onChange={() => {}}
          mx="2"
        />
        <Button onClick={handleCopyClick}>
          {isCopied ? "Copied!" : "Copy"}
        </Button>
      </Flex>
    </>
  );
};

export default ShareLink;
