"use client";
import { useCallback, useEffect, useRef } from "react";
import "@whereby.com/browser-sdk/embed";
import { Box, Button, HStack, useToast, Text } from "@chakra-ui/react";

interface WherebyEmbedProps {
  roomUrl: string;
  onLeave?: () => void;
}

// currently used for webinars only
export default function WherebyWebinarEmbed({
  roomUrl,
  onLeave,
}: WherebyEmbedProps) {
  const wherebyRef = useRef<HTMLElement>(null);

  // TODO extract common toast logic / styles to be used by consent toast on normal rooms
  const toast = useToast();
  useEffect(() => {
    if (roomUrl && !localStorage.getItem("recording-notice-dismissed")) {
      const toastId = toast({
        position: "top",
        duration: null,
        render: ({ onClose }) => (
          <Box p={4} bg="white" borderRadius="md" boxShadow="md">
            <HStack justifyContent="space-between" alignItems="center">
              <Text>
                This webinar is being recorded. By continuing, you agree to our{" "}
                <Button
                  as="a"
                  href="https://monadical.com/privacy"
                  variant="link"
                  color="blue.600"
                  textDecoration="underline"
                  target="_blank"
                >
                  Privacy Policy
                </Button>
              </Text>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => {
                  localStorage.setItem("recording-notice-dismissed", "true");
                  onClose();
                }}
              >
                ✕
              </Button>
            </HStack>
          </Box>
        ),
      });

      return () => {
        toast.close(toastId);
      };
    }
  }, [roomUrl, toast]);

  const handleLeave = () => {
    if (onLeave) {
      onLeave();
    }
  };

  useEffect(() => {
    wherebyRef.current?.addEventListener("leave", handleLeave);

    return () => {
      wherebyRef.current?.removeEventListener("leave", handleLeave);
    };
  }, [handleLeave]);

  return (
    <whereby-embed
      ref={wherebyRef}
      room={roomUrl}
      style={{ width: "100vw", height: "100vh" }}
    />
  );
}
