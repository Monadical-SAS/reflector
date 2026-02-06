import { create, keyResolver, windowScheduler } from "@yornaath/batshit";
import { client } from "./apiClient";
import type { components } from "../reflector-api";

type MeetingStatusResult = {
  roomName: string;
  active_meetings: components["schemas"]["Meeting"][];
  upcoming_events: components["schemas"]["CalendarEventResponse"][];
};

const BATCH_WINDOW_MS = 10;

export function createMeetingStatusBatcher(windowMs: number = BATCH_WINDOW_MS) {
  return create({
    fetcher: async (roomNames: string[]): Promise<MeetingStatusResult[]> => {
      const unique = [...new Set(roomNames)];
      const { data, error } = await client.POST(
        "/v1/rooms/meetings/bulk-status",
        { body: { room_names: unique } },
      );
      if (error || !data) {
        throw new Error(
          `bulk-status fetch failed: ${JSON.stringify(error ?? "no data")}`,
        );
      }
      return roomNames.map((name) => ({
        roomName: name,
        active_meetings: data[name]?.active_meetings ?? [],
        upcoming_events: data[name]?.upcoming_events ?? [],
      }));
    },
    resolver: keyResolver("roomName"),
    scheduler: windowScheduler(windowMs),
  });
}

export const meetingStatusBatcher = createMeetingStatusBatcher();
