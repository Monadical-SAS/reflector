"use client";

import { Flex, Link, Button, Text, HStack } from "@chakra-ui/react";
import NextLink from "next/link";
import Image from "next/image";
import { useRouter } from "next/navigation";

interface MeetingMinimalHeaderProps {
  roomName: string;
  displayName?: string;
  showLeaveButton?: boolean;
  onLeave?: () => void;
  showCreateButton?: boolean;
  onCreateMeeting?: () => void;
  isCreatingMeeting?: boolean;
}

export default function MeetingMinimalHeader({
  roomName,
  displayName,
  showLeaveButton = true,
  onLeave,
  showCreateButton = false,
  onCreateMeeting,
  isCreatingMeeting = false,
}: MeetingMinimalHeaderProps) {
  const router = useRouter();

  const handleLeaveMeeting = () => {
    if (onLeave) {
      onLeave();
    } else {
      router.push(`/${roomName}`);
    }
  };

  const roomTitle = displayName
    ? displayName.endsWith("'s") || displayName.endsWith("s")
      ? `${displayName} Room`
      : `${displayName}'s Room`
    : `${roomName} Room`;

  return (
    <Flex
      as="header"
      justify="space-between"
      alignItems="center"
      w="100%"
      py="2"
      px="4"
      bg="white"
      position="sticky"
      top="0"
      zIndex="10"
    >
      {/* Logo and Room Context */}
      <Flex alignItems="center" gap={3}>
        <Link as={NextLink} href="/" className="flex items-center">
          <Image
            src="/reach.svg"
            width={24}
            height={30}
            className="h-8 w-auto"
            alt="Reflector"
          />
        </Link>
        <Text fontSize="lg" fontWeight="semibold" color="black">
          {roomTitle}
        </Text>
      </Flex>

      {/* Action Buttons */}
      <HStack gap={2}>
        {showCreateButton && onCreateMeeting && (
          <Button
            colorScheme="green"
            size="sm"
            onClick={onCreateMeeting}
            loading={isCreatingMeeting}
            disabled={isCreatingMeeting}
          >
            Create Meeting
          </Button>
        )}
        {showLeaveButton && (
          <Button
            variant="outline"
            colorScheme="gray"
            size="sm"
            onClick={handleLeaveMeeting}
            disabled={isCreatingMeeting}
          >
            Leave Room
          </Button>
        )}
      </HStack>
    </Flex>
  );
}
