import "@testing-library/jest-dom";

// --- Module mocks (hoisted before imports) ---

jest.mock("../apiClient", () => ({
  client: {
    GET: jest.fn(),
    POST: jest.fn(),
    PUT: jest.fn(),
    PATCH: jest.fn(),
    DELETE: jest.fn(),
    use: jest.fn(),
  },
  $api: {
    useQuery: jest.fn(),
    useMutation: jest.fn(),
  },
  API_URL: "http://test",
  WEBSOCKET_URL: "ws://test",
  configureApiAuth: jest.fn(),
}));

jest.mock("../AuthProvider", () => ({
  useAuth: () => ({
    status: "authenticated" as const,
    accessToken: "test-token",
    accessTokenExpires: Date.now() + 3600000,
    user: { id: "user1", name: "Test User" },
    update: jest.fn(),
    signIn: jest.fn(),
    signOut: jest.fn(),
    lastUserId: "user1",
  }),
}));

// Recreate the batcher with a 0ms window. setTimeout(fn, 0) defers to the next
// macrotask boundary — after all synchronous React rendering completes. All
// useQuery queryFns fire within the same macrotask, so they all queue into one
// batch before the timer fires. This is deterministic and avoids fake timers.
jest.mock("../meetingStatusBatcher", () => {
  const actual = jest.requireActual("../meetingStatusBatcher");
  return {
    ...actual,
    meetingStatusBatcher: actual.createMeetingStatusBatcher(0),
  };
});

// --- Imports (after mocks) ---

import React from "react";
import { render, waitFor, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useRoomActiveMeetings, useRoomUpcomingMeetings } from "../apiHooks";
import { client } from "../apiClient";
import { ErrorProvider } from "../../(errors)/errorContext";

const mockClient = client as { POST: jest.Mock };

// --- Helpers ---

function mockBulkStatusEndpoint(
  roomData?: Record<
    string,
    { active_meetings: unknown[]; upcoming_events: unknown[] }
  >,
) {
  mockClient.POST.mockImplementation(
    async (_path: string, options: { body: { room_names: string[] } }) => {
      const roomNames: string[] = options.body.room_names;
      const data = roomData
        ? Object.fromEntries(
            roomNames.map((name) => [
              name,
              roomData[name] ?? { active_meetings: [], upcoming_events: [] },
            ]),
          )
        : Object.fromEntries(
            roomNames.map((name) => [
              name,
              { active_meetings: [], upcoming_events: [] },
            ]),
          );
      return { data, error: undefined, response: {} };
    },
  );
}

// --- Test component: renders N room cards, each using both hooks ---

function RoomCard({ roomName }: { roomName: string }) {
  const active = useRoomActiveMeetings(roomName);
  const upcoming = useRoomUpcomingMeetings(roomName);

  if (active.isLoading || upcoming.isLoading) {
    return <div data-testid={`room-${roomName}`}>loading</div>;
  }

  return (
    <div data-testid={`room-${roomName}`}>
      {active.data?.length ?? 0} active, {upcoming.data?.length ?? 0} upcoming
    </div>
  );
}

function RoomList({ roomNames }: { roomNames: string[] }) {
  return (
    <>
      {roomNames.map((name) => (
        <RoomCard key={name} roomName={name} />
      ))}
    </>
  );
}

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <ErrorProvider>{children}</ErrorProvider>
      </QueryClientProvider>
    );
  };
}

// --- Tests ---

describe("meeting status batcher integration", () => {
  afterEach(() => jest.clearAllMocks());

  it("batches multiple room queries into a single POST request", async () => {
    const rooms = Array.from({ length: 10 }, (_, i) => `room-${i}`);

    mockBulkStatusEndpoint();

    render(<RoomList roomNames={rooms} />, { wrapper: createWrapper() });

    await waitFor(() => {
      for (const name of rooms) {
        expect(screen.getByTestId(`room-${name}`)).toHaveTextContent(
          "0 active, 0 upcoming",
        );
      }
    });

    const postCalls = mockClient.POST.mock.calls.filter(
      ([path]: [string]) => path === "/v1/rooms/meetings/bulk-status",
    );

    // Without batching this would be 20 calls (2 hooks x 10 rooms).
    // With the 200ms test window, all queries land in one batch → exactly 1 POST.
    expect(postCalls).toHaveLength(1);

    // The single call should contain all 10 rooms (deduplicated)
    const requestedRooms: string[] = postCalls[0][1].body.room_names;
    for (const name of rooms) {
      expect(requestedRooms).toContain(name);
    }
  });

  it("batcher fetcher returns room-specific data", async () => {
    const {
      meetingStatusBatcher: batcher,
    } = require("../meetingStatusBatcher");

    mockBulkStatusEndpoint({
      "room-a": {
        active_meetings: [{ id: "m1", room_name: "room-a" }],
        upcoming_events: [],
      },
      "room-b": {
        active_meetings: [],
        upcoming_events: [{ id: "e1", title: "Standup" }],
      },
    });

    const [resultA, resultB] = await Promise.all([
      batcher.fetch("room-a"),
      batcher.fetch("room-b"),
    ]);

    expect(mockClient.POST).toHaveBeenCalledTimes(1);
    expect(resultA.active_meetings).toEqual([
      { id: "m1", room_name: "room-a" },
    ]);
    expect(resultA.upcoming_events).toEqual([]);
    expect(resultB.active_meetings).toEqual([]);
    expect(resultB.upcoming_events).toEqual([{ id: "e1", title: "Standup" }]);
  });

  it("renders room-specific meeting data through hooks", async () => {
    mockBulkStatusEndpoint({
      "room-a": {
        active_meetings: [{ id: "m1", room_name: "room-a" }],
        upcoming_events: [],
      },
      "room-b": {
        active_meetings: [],
        upcoming_events: [{ id: "e1", title: "Standup" }],
      },
    });

    render(<RoomList roomNames={["room-a", "room-b"]} />, {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(screen.getByTestId("room-room-a")).toHaveTextContent(
        "1 active, 0 upcoming",
      );
      expect(screen.getByTestId("room-room-b")).toHaveTextContent(
        "0 active, 1 upcoming",
      );
    });
  });
});
