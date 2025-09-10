"use client";
import { useCallback, useEffect, useRef } from "react";
import "@whereby.com/browser-sdk/embed";
import { Box, Button, HStack, Text, Link } from "@chakra-ui/react";
import { toaster } from "../components/ui/toaster";

interface WherebyEmbedProps {
  roomUrl: string;
  onLeave?: () => void;
  isWebinar?: boolean;
}

// used for both webinars and meetings
export default function WherebyWebinarEmbed({
  roomUrl,
  onLeave,
  isWebinar = false,
}: WherebyEmbedProps) {
  const wherebyRef = useRef<HTMLElement>(null);

  // TODO extract common toast logic / styles to be used by consent toast on normal rooms
  useEffect(() => {
    if (roomUrl && !localStorage.getItem("recording-notice-dismissed")) {
      const toastIdPromise = toaster.create({
        placement: "top",
        duration: null,
        render: ({ dismiss }) => (
          <Box p={4} bg="white" borderRadius="md" boxShadow="md">
            <HStack justifyContent="space-between" alignItems="center">
              <Text>
                This {isWebinar ? "webinar" : "meeting"} is being recorded. By
                continuing, you agree to our{" "}
                <Link
                  href="https://monadical.com/privacy"
                  color="blue.600"
                  textDecoration="underline"
                  target="_blank"
                >
                  Privacy Policy
                </Link>
              </Text>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => {
                  localStorage.setItem("recording-notice-dismissed", "true");
                  dismiss();
                }}
              >
                ✕
              </Button>
            </HStack>
          </Box>
        ),
      });

      return () => {
        toastIdPromise.then((id) => toaster.dismiss(id));
      };
    }
  }, [roomUrl]);

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
