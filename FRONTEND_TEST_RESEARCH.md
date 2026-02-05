# Frontend Hook Testing Research

## Context

Hooks in `www/app/lib/apiHooks.ts` use two patterns:
1. `$api.useQuery("get", "/v1/rooms", ...)` -- openapi-react-query wrapping openapi-fetch
2. `useQuery({ queryFn: () => meetingStatusBatcher.fetch(roomName!) })` -- plain react-query with batshit batcher

Key dependencies: module-level `client` and `$api` in `apiClient.tsx`, module-level `meetingStatusBatcher` in `meetingStatusBatcher.ts`, `useAuth()` context, `useError()` context.

---

## 1. Recommended Mocking Strategy

**Use `jest.mock()` on the module-level clients + `renderHook` from `@testing-library/react`.**

Reasons against MSW:
- `openapi-fetch` creates its `client` at module import time. MSW's `server.listen()` must run before the client is created (see [openapi-ts/openapi-typescript#1878](https://github.com/openapi-ts/openapi-typescript/issues/1878)). This requires dynamic imports or Proxy workarounds -- fragile.
- MSW adds infrastructure overhead (handlers, server lifecycle) for unit tests that only need to verify hook behavior.
- The batcher calls `client.POST(...)` directly, not `fetch()`. Mocking the client is more direct.

Reasons against `openapi-fetch-mock` middleware:
- Requires `client.use()` / `client.eject()` per test -- less isolated than module mock.
- Our `client` already has auth middleware; test middleware ordering gets messy.

**Winner: Direct module mocking with `jest.mock()`.**

### Pattern for `$api` hooks

Mock the entire `apiClient` module. The `$api.useQuery` / `$api.useMutation` from openapi-react-query are just wrappers around react-query that call `client.GET`, `client.POST`, etc. Mock at the `client` method level:

```ts
// __mocks__ or inline
jest.mock("../apiClient", () => {
  const mockClient = {
    GET: jest.fn(),
    POST: jest.fn(),
    PUT: jest.fn(),
    PATCH: jest.fn(),
    DELETE: jest.fn(),
    use: jest.fn(),
  };
  const createFetchClient = require("openapi-react-query").default;
  return {
    client: mockClient,
    $api: createFetchClient(mockClient),
    API_URL: "http://test",
    WEBSOCKET_URL: "ws://test",
    configureApiAuth: jest.fn(),
  };
});
```

**Problem**: `openapi-react-query` calls `client.GET(path, init)` and expects `{ data, error, response }`. So the mock must return that shape:

```ts
import { client } from "../apiClient";
const mockClient = client as jest.Mocked<typeof client>;

mockClient.GET.mockResolvedValue({
  data: { items: [], total: 0 },
  error: undefined,
  response: new Response(),
});
```

### Pattern for batcher hooks

Mock the batcher module:

```ts
jest.mock("../meetingStatusBatcher", () => ({
  meetingStatusBatcher: {
    fetch: jest.fn(),
  },
}));

import { meetingStatusBatcher } from "../meetingStatusBatcher";
const mockBatcher = meetingStatusBatcher as jest.Mocked<typeof meetingStatusBatcher>;

mockBatcher.fetch.mockResolvedValue({
  roomName: "test-room",
  active_meetings: [{ id: "m1" }],
  upcoming_events: [],
});
```

---

## 2. renderHook: Use `@testing-library/react` (NOT `@testing-library/react-hooks`)

`@testing-library/react-hooks` is **deprecated** since React 18. The `renderHook` function is now built into `@testing-library/react` v13+.

```ts
import { renderHook, waitFor } from "@testing-library/react";
```

Key differences from the old package:
- No `waitForNextUpdate` -- use `waitFor(() => expect(...))` instead
- No separate `result.current.error` for error boundaries
- Works with React 18 concurrent features

---

## 3. Mocking/Intercepting openapi-fetch Client

Three viable approaches ranked by simplicity:

### A. Mock the module (recommended)

As shown above. `jest.mock("../apiClient")` replaces the entire module. The `$api` wrapper can be reconstructed from the mock client using the real `openapi-react-query` factory, or you can mock `$api` methods directly.

**Caveat**: If you reconstruct `$api` from a mock client, `$api.useQuery` will actually call `mockClient.GET(path, init)`. This is good -- it tests the integration between openapi-react-query and the client.

### B. Inject mock fetch into client

```ts
const mockFetch = jest.fn().mockResolvedValue(
  new Response(JSON.stringify({ data: "test" }), { status: 200 })
);
const testClient = createClient<paths>({ baseUrl: "http://test", fetch: mockFetch });
```

Problem: requires the hooks to accept the client as a parameter or use dependency injection. Our hooks use module-level `$api` -- doesn't work without refactoring.

### C. MSW (not recommended for unit tests)

As discussed, the module-import-time client creation conflicts with MSW's server lifecycle. Workable but fragile.

---

## 4. Testing Batshit Batcher Behavior

### Unit test the batcher directly (no hooks)

The batcher is a pure module -- test it without React:

```ts
import { create, keyResolver, windowScheduler } from "@yornaath/batshit";

test("batches multiple room queries into one POST", async () => {
  const mockPost = jest.fn().mockResolvedValue({
    data: {
      "room-a": { active_meetings: [], upcoming_events: [] },
      "room-b": { active_meetings: [], upcoming_events: [] },
    },
  });

  const batcher = create({
    fetcher: async (roomNames: string[]) => {
      const unique = [...new Set(roomNames)];
      const { data } = await mockPost("/v1/rooms/meetings/bulk-status", {
        body: { room_names: unique },
      });
      return roomNames.map((name) => ({
        roomName: name,
        active_meetings: data?.[name]?.active_meetings ?? [],
        upcoming_events: data?.[name]?.upcoming_events ?? [],
      }));
    },
    resolver: keyResolver("roomName"),
    scheduler: windowScheduler(10),
  });

  // Fire multiple fetches within the 10ms window
  const [resultA, resultB] = await Promise.all([
    batcher.fetch("room-a"),
    batcher.fetch("room-b"),
  ]);

  // Only one POST call
  expect(mockPost).toHaveBeenCalledTimes(1);
  expect(mockPost).toHaveBeenCalledWith("/v1/rooms/meetings/bulk-status", {
    body: { room_names: ["room-a", "room-b"] },
  });

  expect(resultA.active_meetings).toEqual([]);
  expect(resultB.active_meetings).toEqual([]);
});

test("deduplicates same room name", async () => {
  const mockPost = jest.fn().mockResolvedValue({
    data: { "room-a": { active_meetings: [{ id: "m1" }], upcoming_events: [] } },
  });

  const batcher = create({
    fetcher: async (roomNames: string[]) => {
      const unique = [...new Set(roomNames)];
      const { data } = await mockPost("/v1/rooms/meetings/bulk-status", {
        body: { room_names: unique },
      });
      return roomNames.map((name) => ({
        roomName: name,
        active_meetings: data?.[name]?.active_meetings ?? [],
        upcoming_events: data?.[name]?.upcoming_events ?? [],
      }));
    },
    resolver: keyResolver("roomName"),
    scheduler: windowScheduler(10),
  });

  const [r1, r2] = await Promise.all([
    batcher.fetch("room-a"),
    batcher.fetch("room-a"),
  ]);

  expect(mockPost).toHaveBeenCalledTimes(1);
  // Both resolve to same data
  expect(r1.active_meetings).toEqual([{ id: "m1" }]);
  expect(r2.active_meetings).toEqual([{ id: "m1" }]);
});
```

### Test the actual batcher module with mocked client

```ts
jest.mock("../apiClient", () => ({
  client: { POST: jest.fn() },
}));

import { client } from "../apiClient";
import { meetingStatusBatcher } from "../meetingStatusBatcher";

const mockClient = client as jest.Mocked<typeof client>;

test("meetingStatusBatcher calls bulk-status endpoint", async () => {
  mockClient.POST.mockResolvedValue({
    data: { "room-x": { active_meetings: [], upcoming_events: [] } },
    error: undefined,
    response: new Response(),
  });

  const result = await meetingStatusBatcher.fetch("room-x");
  expect(result.active_meetings).toEqual([]);
  expect(mockClient.POST).toHaveBeenCalledWith(
    "/v1/rooms/meetings/bulk-status",
    expect.objectContaining({ body: { room_names: ["room-x"] } }),
  );
});
```

---

## 5. Minimal Jest Setup

### Install dependencies

```bash
cd www && pnpm add -D @testing-library/react @testing-library/jest-dom jest-environment-jsdom
```

Note: `jest` v30 and `ts-jest` are already in devDependencies. `@types/jest` v30 is already present. `@testing-library/react` v16 supports React 18.

### jest.config.ts

```ts
import type { Config } from "jest";

const config: Config = {
  testEnvironment: "jest-environment-jsdom",
  transform: {
    "^.+\\.tsx?$": ["ts-jest", {
      tsconfig: "tsconfig.json",
    }],
  },
  moduleNameMapper: {
    // Handle module aliases if you add them later
    // "^@/(.*)$": "<rootDir>/$1",
  },
  setupFilesAfterSetup: ["<rootDir>/jest.setup.ts"],
  // Ignore Next.js build output
  testPathIgnorePatterns: ["<rootDir>/.next/", "<rootDir>/node_modules/"],
};

export default config;
```

### jest.setup.ts

```ts
import "@testing-library/jest-dom";
```

### Mocking modules that fail in jsdom

The `apiClient.tsx` module calls `getSession()` and `getClientEnv()` at import time. These will fail in jsdom. Mock them:

```ts
// In test file or __mocks__
jest.mock("next-auth/react", () => ({
  getSession: jest.fn().mockResolvedValue(null),
  signIn: jest.fn(),
  signOut: jest.fn(),
  useSession: jest.fn().mockReturnValue({ data: null, status: "unauthenticated" }),
}));

jest.mock("../next", () => ({
  isBuildPhase: false,
}));

jest.mock("../clientEnv", () => ({
  getClientEnv: () => ({
    API_URL: "http://test-api",
    WEBSOCKET_URL: "ws://test-api",
    FEATURE_REQUIRE_LOGIN: false,
    FEATURE_PRIVACY: null,
    FEATURE_BROWSE: null,
    FEATURE_SEND_TO_ZULIP: null,
    FEATURE_ROOMS: null,
  }),
}));
```

---

## 6. Testing Hooks Without Prop-Based DI

The hooks use module-level `$api` and `meetingStatusBatcher`. No way to inject via props. Two approaches:

### A. `jest.mock()` the modules (recommended)

Already shown. Works cleanly. Each test can `mockResolvedValue` differently.

### B. Manual mock files (`__mocks__/`)

Create `www/app/lib/__mocks__/apiClient.tsx`:

```ts
const mockClient = {
  GET: jest.fn(),
  POST: jest.fn(),
  PUT: jest.fn(),
  PATCH: jest.fn(),
  DELETE: jest.fn(),
  use: jest.fn(),
};

// Use real openapi-react-query wrapping the mock client
const createFetchClient = jest.requireActual("openapi-react-query").default;

export const client = mockClient;
export const $api = createFetchClient(mockClient);
export const API_URL = "http://test";
export const WEBSOCKET_URL = "ws://test";
export const configureApiAuth = jest.fn();
```

Then in tests: `jest.mock("../apiClient")` with no factory -- picks up the `__mocks__` file automatically.

---

## 7. Complete Example Test

```ts
// www/app/lib/__tests__/apiHooks.test.ts

import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";

// Mock modules before imports
jest.mock("next-auth/react", () => ({
  getSession: jest.fn().mockResolvedValue(null),
  signIn: jest.fn(),
  signOut: jest.fn(),
  useSession: jest.fn().mockReturnValue({
    data: null,
    status: "unauthenticated",
  }),
}));

jest.mock("../clientEnv", () => ({
  getClientEnv: () => ({
    API_URL: "http://test",
    WEBSOCKET_URL: "ws://test",
    FEATURE_REQUIRE_LOGIN: false,
    FEATURE_PRIVACY: null,
    FEATURE_BROWSE: null,
    FEATURE_SEND_TO_ZULIP: null,
    FEATURE_ROOMS: null,
  }),
}));

jest.mock("../next", () => ({ isBuildPhase: false }));

jest.mock("../meetingStatusBatcher", () => ({
  meetingStatusBatcher: { fetch: jest.fn() },
}));

// Must mock apiClient BEFORE importing hooks
jest.mock("../apiClient", () => {
  const mockClient = {
    GET: jest.fn(),
    POST: jest.fn(),
    PATCH: jest.fn(),
    DELETE: jest.fn(),
    use: jest.fn(),
  };
  const createFetchClient =
    jest.requireActual("openapi-react-query").default;
  return {
    client: mockClient,
    $api: createFetchClient(mockClient),
    API_URL: "http://test",
    WEBSOCKET_URL: "ws://test",
    configureApiAuth: jest.fn(),
  };
});

// Now import the hooks under test
import { useRoomActiveMeetings, useTranscriptsSearch } from "../apiHooks";
import { client } from "../apiClient";
import { meetingStatusBatcher } from "../meetingStatusBatcher";
import { ErrorProvider } from "../../(errors)/errorContext";

const mockClient = client as jest.Mocked<typeof client>;
const mockBatcher = meetingStatusBatcher as { fetch: jest.Mock };

// Wrapper with required providers
function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return React.createElement(
      QueryClientProvider,
      { client: queryClient },
      React.createElement(ErrorProvider, null, children),
    );
  };
}

describe("useRoomActiveMeetings", () => {
  afterEach(() => jest.clearAllMocks());

  it("returns active meetings from batcher", async () => {
    mockBatcher.fetch.mockResolvedValue({
      roomName: "test-room",
      active_meetings: [{ id: "m1", room_name: "test-room" }],
      upcoming_events: [],
    });

    const { result } = renderHook(
      () => useRoomActiveMeetings("test-room"),
      { wrapper: createWrapper() },
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual([
      { id: "m1", room_name: "test-room" },
    ]);
    expect(mockBatcher.fetch).toHaveBeenCalledWith("test-room");
  });

  it("is disabled when roomName is null", () => {
    const { result } = renderHook(
      () => useRoomActiveMeetings(null),
      { wrapper: createWrapper() },
    );

    expect(result.current.fetchStatus).toBe("idle");
    expect(mockBatcher.fetch).not.toHaveBeenCalled();
  });
});

describe("useTranscriptsSearch", () => {
  afterEach(() => jest.clearAllMocks());

  it("fetches transcripts via $api", async () => {
    mockClient.GET.mockResolvedValue({
      data: { items: [{ id: "t1", title: "Test" }], total: 1 },
      error: undefined,
      response: new Response(),
    });

    const { result } = renderHook(
      () => useTranscriptsSearch("hello"),
      { wrapper: createWrapper() },
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual({
      items: [{ id: "t1", title: "Test" }],
      total: 1,
    });
    expect(mockClient.GET).toHaveBeenCalledWith(
      "/v1/transcripts/search",
      expect.objectContaining({
        params: expect.objectContaining({
          query: expect.objectContaining({ q: "hello" }),
        }),
      }),
    );
  });
});
```

---

## 8. Summary of Decisions

| Question | Answer |
|----------|--------|
| Mocking approach | `jest.mock()` on module-level clients |
| renderHook source | `@testing-library/react` (not deprecated hooks lib) |
| Intercept openapi-fetch | Mock `client.GET/POST/...` methods, reconstruct `$api` with real `openapi-react-query` |
| Test batcher | Unit test batcher directly with mock POST fn; test hooks with mock batcher module |
| Auth context | Mock `next-auth/react`, disable `requireLogin` feature flag |
| Error context | Wrap with real `ErrorProvider` (it's simple state) |
| QueryClient | New instance per test, `retry: false` |

### New packages needed

```bash
cd www && pnpm add -D @testing-library/react @testing-library/jest-dom @testing-library/dom jest-environment-jsdom
```

### Files to create

1. `www/jest.config.ts` -- jest configuration
2. `www/jest.setup.ts` -- `import "@testing-library/jest-dom"`
3. `www/app/lib/__tests__/apiHooks.test.ts` -- hook tests
4. `www/app/lib/__tests__/meetingStatusBatcher.test.ts` -- batcher unit tests

### Potential issues

- `ts-jest` v29 may not fully support Jest 30. Watch for compatibility errors. May need `ts-jest@next` or switch to `@swc/jest`.
- `openapi-react-query` imports may need ESM handling in Jest. If `jest.requireActual("openapi-react-query")` fails, mock `$api` methods directly instead of reconstructing.
- `"use client"` directive at top of `apiHooks.ts` / `apiClient.tsx` -- Jest ignores this (it's a no-op outside Next.js bundler), but verify it doesn't cause parse errors.
