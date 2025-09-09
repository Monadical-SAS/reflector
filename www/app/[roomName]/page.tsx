import { Metadata } from "next";
import RoomClient from "./RoomClient";

export type RoomDetails = {
  params: {
    roomName: string;
  };
};

// Generate dynamic metadata for the room selection page
export async function generateMetadata({
  params,
}: RoomDetails): Promise<Metadata> {
  const { roomName } = params;

  try {
    // Fetch room data server-side for metadata
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
        title: `${displayName} Room - Select a Meeting`,
        description: `Join a meeting in ${displayName}'s room on Reflector.`,
      };
    }
  } catch (error) {
    console.error("Failed to fetch room for metadata:", error);
  }

  // Fallback if room fetch fails
  return {
    title: `${roomName} Room - Select a Meeting`,
    description: `Join a meeting in ${roomName}'s room on Reflector.`,
  };
}

export default function Room(details: RoomDetails) {
  return <RoomClient params={details.params} />;
}
