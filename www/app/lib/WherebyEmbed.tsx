"use client";
import { useEffect, useRef } from "react";
import "@whereby.com/browser-sdk/embed";
import { Box, Button, HStack, useToast, Text } from "@chakra-ui/react";

interface WherebyEmbedProps {
  roomUrl: string;
}

export default function WherebyEmbed({ roomUrl }: WherebyEmbedProps) {
  const wherebyRef = useRef<HTMLElement>(null);

  const toast = useToast();
  useEffect(() => {
    if (roomUrl && !localStorage.getItem("recording-notice-dismissed")) {
      const toastId = toast({
        position: "top",
        duration: null,
        render: ({ onClose }) => (
          <Box p={4} bg="white" borderRadius="md" boxShadow="md">
            <HStack justify="space-between" align="center">
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

  return (
    <whereby-embed
      ref={wherebyRef}
      room={roomUrl}
      style={{ width: "100vw", height: "100vh" }}
    />
  );
}
