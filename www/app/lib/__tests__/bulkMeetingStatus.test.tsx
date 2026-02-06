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
    queryOptions: (method: string, path: string, init?: unknown) =>
      init === undefined
        ? { queryKey: [method, path] }
        : { queryKey: [method, path, init] },
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

// --- Imports (after mocks) ---

import React from "react";
import { render, waitFor, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useRoomsBulkMeetingStatus, BulkMeetingStatusMap } from "../apiHooks";
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
      const src = roomData ?? {};
      const data = Object.fromEntries(
        roomNames.map((name) => [
          name,
          src[name] ?? { active_meetings: [], upcoming_events: [] },
        ]),
      );
      return { data, error: undefined, response: {} };
    },
  );
}

// --- Test component: uses the bulk hook and displays results ---

function BulkStatusDisplay({ roomNames }: { roomNames: string[] }) {
  const { data, isLoading } = useRoomsBulkMeetingStatus(roomNames);

  if (isLoading) {
    return <div data-testid="status">loading</div>;
  }

  if (!data) {
    return <div data-testid="status">no data</div>;
  }

  return (
    <div data-testid="status">
      {roomNames.map((name) => {
        const status = data[name];
        return (
          <div key={name} data-testid={`room-${name}`}>
            {status?.active_meetings?.length ?? 0} active,{" "}
            {status?.upcoming_events?.length ?? 0} upcoming
          </div>
        );
      })}
    </div>
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

describe("bulk meeting status (prop-drilling)", () => {
  afterEach(() => jest.clearAllMocks());

  it("fetches all room statuses in a single POST request", async () => {
    const rooms = Array.from({ length: 10 }, (_, i) => `room-${i}`);

    mockBulkStatusEndpoint();

    render(<BulkStatusDisplay roomNames={rooms} />, {
      wrapper: createWrapper(),
    });

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

    // Prop-drilling: exactly 1 POST for all rooms (no batcher needed)
    expect(postCalls).toHaveLength(1);

    // The single call contains all room names
    const requestedRooms: string[] = postCalls[0][1].body.room_names;
    expect(requestedRooms).toHaveLength(10);
    for (const name of rooms) {
      expect(requestedRooms).toContain(name);
    }
  });

  it("returns room-specific data correctly", async () => {
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

    render(<BulkStatusDisplay roomNames={["room-a", "room-b"]} />, {
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

    // Still just 1 POST
    expect(mockClient.POST).toHaveBeenCalledTimes(1);
  });

  it("does not fetch when roomNames is empty", async () => {
    mockBulkStatusEndpoint();

    render(<BulkStatusDisplay roomNames={[]} />, {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(screen.getByTestId("status")).toHaveTextContent("no data");
    });

    // No POST calls when no rooms
    expect(mockClient.POST).not.toHaveBeenCalled();
  });

  it("surfaces error when POST fails", async () => {
    mockClient.POST.mockResolvedValue({
      data: undefined,
      error: { detail: "server error" },
      response: {},
    });

    function ErrorDisplay({ roomNames }: { roomNames: string[] }) {
      const { error } = useRoomsBulkMeetingStatus(roomNames);
      if (error) return <div data-testid="error">{error.message}</div>;
      return <div data-testid="error">no error</div>;
    }

    render(<ErrorDisplay roomNames={["room-x"]} />, {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(screen.getByTestId("error")).toHaveTextContent(
        "bulk-status fetch failed",
      );
    });
  });

  it("does not fetch when unauthenticated", async () => {
    // Override useAuth to return unauthenticated
    const authModule = jest.requireMock("../AuthProvider");
    const originalUseAuth = authModule.useAuth;
    authModule.useAuth = () => ({
      ...originalUseAuth(),
      status: "unauthenticated",
    });

    mockBulkStatusEndpoint();

    render(<BulkStatusDisplay roomNames={["room-1"]} />, {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(screen.getByTestId("status")).toHaveTextContent("no data");
    });

    expect(mockClient.POST).not.toHaveBeenCalled();

    // Restore
    authModule.useAuth = originalUseAuth;
  });
});
