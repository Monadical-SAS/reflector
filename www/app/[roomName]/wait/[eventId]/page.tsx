import {
  Box,
  Spinner,
  Text,
  VStack,
  Button,
  HStack,
  Badge,
} from "@chakra-ui/react";
import MinimalHeader from "../../../components/MinimalHeader";
import { Metadata } from "next";
import WaitPageClient from "./WaitPageClient";

interface WaitPageProps {
  params: {
    roomName: string;
    eventId: string;
  };
}

// Generate dynamic metadata for the waiting page
export async function generateMetadata({
  params,
}: WaitPageProps): Promise<Metadata> {
  const { roomName } = params;

  try {
    const response = await fetch(
      `${process.env.NEXT_PUBLIC_REFLECTOR_API_URL}/v1/rooms/name/${roomName}`,
      {
        headers: {
          "Content-Type": "application/json",
        },
      },
    );

    if (response.ok) {
      const room = await response.json();
      const displayName = room.display_name || room.name;
      return {
        title: `Waiting for Meeting - ${displayName}'s Room`,
        description: `Waiting for upcoming meeting in ${displayName}'s room on Reflector.`,
      };
    }
  } catch (error) {
    console.error("Failed to fetch room for metadata:", error);
  }

  return {
    title: `Waiting for Meeting - ${roomName}'s Room`,
    description: `Waiting for upcoming meeting in ${roomName}'s room on Reflector.`,
  };
}

export default function WaitPage({ params }: WaitPageProps) {
  return <WaitPageClient params={params} />;
}
