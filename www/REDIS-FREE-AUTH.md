# Redis-Free Authentication Solution for Reflector

## Problem Analysis

### The Multi-Tab Race Condition

The current implementation uses Redis to solve a specific problem:

- NextAuth's `useSession` hook broadcasts `getSession` events across all open tabs
- When a token expires, all tabs simultaneously try to refresh it
- Multiple refresh attempts with the same refresh_token cause 400 errors
- Redis + Redlock ensures only one refresh happens at a time

### Root Cause

The issue stems from **client-side broadcasting**, not from NextAuth itself. The `useSession` hook creates a BroadcastChannel that syncs sessions across tabs, triggering the race condition.

## Solution: Middleware-Based Token Refresh

Move token refresh from client-side to server-side middleware, eliminating broadcasting and race conditions entirely.

### Implementation

#### 1. Enhanced Middleware (`middleware.ts`)

```typescript
import { withAuth } from "next-auth/middleware";
import { getToken } from "next-auth/jwt";
import { encode } from "next-auth/jwt";
import { NextResponse } from "next/server";
import { getConfig } from "./app/lib/configProvider";

const REFRESH_THRESHOLD = 60 * 1000; // 60 seconds before expiry

async function refreshAccessToken(token: JWT): Promise<JWT> {
  try {
    const response = await fetch(process.env.AUTHENTIK_REFRESH_TOKEN_URL!, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: new URLSearchParams({
        client_id: process.env.AUTHENTIK_CLIENT_ID!,
        client_secret: process.env.AUTHENTIK_CLIENT_SECRET!,
        grant_type: "refresh_token",
        refresh_token: token.refreshToken as string,
      }),
    });

    if (!response.ok) throw new Error("Failed to refresh token");

    const refreshedTokens = await response.json();
    return {
      ...token,
      accessToken: refreshedTokens.access_token,
      accessTokenExpires: Date.now() + refreshedTokens.expires_in * 1000,
      refreshToken: refreshedTokens.refresh_token || token.refreshToken,
    };
  } catch (error) {
    return { ...token, error: "RefreshAccessTokenError" };
  }
}

export default withAuth(
  async function middleware(request) {
    const config = await getConfig();
    const pathname = request.nextUrl.pathname;

    // Feature flag checks (existing)
    if (
      (!config.features.browse && pathname.startsWith("/browse")) ||
      (!config.features.rooms && pathname.startsWith("/rooms"))
    ) {
      return NextResponse.redirect(request.nextUrl.origin);
    }

    // Token refresh logic (new)
    const token = await getToken({ req: request });

    if (token && token.accessTokenExpires) {
      const timeUntilExpiry = (token.accessTokenExpires as number) - Date.now();

      // Refresh if within threshold and not already expired
      if (timeUntilExpiry > 0 && timeUntilExpiry < REFRESH_THRESHOLD) {
        try {
          const refreshedToken = await refreshAccessToken(token);

          if (!refreshedToken.error) {
            // Encode new token
            const newSessionToken = await encode({
              secret: process.env.NEXTAUTH_SECRET!,
              token: refreshedToken,
              maxAge: 30 * 24 * 60 * 60, // 30 days
            });

            // Update cookie
            const response = NextResponse.next();
            response.cookies.set({
              name:
                process.env.NODE_ENV === "production"
                  ? "__Secure-next-auth.session-token"
                  : "next-auth.session-token",
              value: newSessionToken,
              httpOnly: true,
              secure: process.env.NODE_ENV === "production",
              sameSite: "lax",
            });

            return response;
          }
        } catch (error) {
          console.error("Token refresh in middleware failed:", error);
        }
      }
    }

    return NextResponse.next();
  },
  {
    callbacks: {
      async authorized({ req, token }) {
        const config = await getConfig();

        if (
          config.features.requireLogin &&
          PROTECTED_PAGES.test(req.nextUrl.pathname)
        ) {
          return !!token;
        }

        return true;
      },
    },
  },
);
```

#### 2. Simplified auth.ts (No Redis)

```typescript
import { AuthOptions } from "next-auth";
import AuthentikProvider from "next-auth/providers/authentik";
import { JWT } from "next-auth/jwt";
import { JWTWithAccessToken, CustomSession } from "./types";

const PRETIMEOUT = 60; // seconds before token expires

export const authOptions: AuthOptions = {
  providers: [
    AuthentikProvider({
      clientId: process.env.AUTHENTIK_CLIENT_ID as string,
      clientSecret: process.env.AUTHENTIK_CLIENT_SECRET as string,
      issuer: process.env.AUTHENTIK_ISSUER,
      authorization: {
        params: {
          scope: "openid email profile offline_access",
        },
      },
    }),
  ],
  session: {
    strategy: "jwt",
    maxAge: 30 * 24 * 60 * 60, // 30 days
  },
  callbacks: {
    async jwt({ token, account, user }) {
      // Initial sign in
      if (account && user) {
        return {
          ...token,
          accessToken: account.access_token,
          accessTokenExpires: (account.expires_at as number) * 1000,
          refreshToken: account.refresh_token, // Store in JWT
        } as JWTWithAccessToken;
      }

      // Return token as-is (refresh happens in middleware)
      return token;
    },

    async session({ session, token }) {
      const extendedToken = token as JWTWithAccessToken;
      const customSession = session as CustomSession;

      customSession.accessToken = extendedToken.accessToken;
      customSession.accessTokenExpires = extendedToken.accessTokenExpires;
      customSession.error = extendedToken.error;
      customSession.user = {
        id: extendedToken.sub,
        name: extendedToken.name,
        email: extendedToken.email,
      };

      return customSession;
    },
  },
};
```

#### 3. Remove Client-Side Auto-Refresh

**Delete:** `app/lib/SessionAutoRefresh.tsx`

**Update:** `app/lib/SessionProvider.tsx`

```typescript
"use client";
import { SessionProvider as SessionProviderNextAuth } from "next-auth/react";

export default function SessionProvider({ children }) {
  return (
    <SessionProviderNextAuth>
      {children}
    </SessionProviderNextAuth>
  );
}
```

### Alternative: Client-Side Deduplication (If Keeping useSession)

If you need to keep client-side session features, implement request deduplication:

```typescript
// app/lib/deduplicatedSession.ts
let refreshPromise: Promise<any> | null = null;

export async function deduplicatedRefresh() {
  if (!refreshPromise) {
    refreshPromise = fetch("/api/auth/session", {
      method: "GET",
    }).finally(() => {
      refreshPromise = null;
    });
  }
  return refreshPromise;
}

// Modified SessionAutoRefresh.tsx
export function SessionAutoRefresh({ children }) {
  const { data: session } = useSession();

  useEffect(() => {
    const interval = setInterval(async () => {
      if (shouldRefresh(session)) {
        await deduplicatedRefresh(); // Use deduplicated call
      }
    }, 20000);

    return () => clearInterval(interval);
  }, [session]);

  return children;
}
```

## Benefits of Middleware Approach

### Advantages

1. **No Race Conditions**: Each request handled independently server-side
2. **No Redis Required**: Eliminates infrastructure dependency
3. **No Broadcasting**: No multi-tab synchronization issues
4. **Automatic**: Refreshes on navigation, no polling needed
5. **Simpler**: Less client-side complexity
6. **Performance**: No unnecessary API calls from multiple tabs

### Trade-offs

1. **Long-lived pages**: Won't refresh without navigation
   - Mitigation: Keep minimal client-side refresh for critical pages
2. **Server load**: Each request checks token
   - Mitigation: Only checks protected routes
3. **Cookie size**: Refresh token stored in JWT
   - Acceptable: ~200-300 bytes increase

## Migration Path

### Phase 1: Implement Middleware Refresh

1. Update middleware.ts with token refresh logic
2. Test with existing Redis-based auth.ts
3. Verify refresh works on navigation

### Phase 2: Remove Redis

1. Update auth.ts to store refresh_token in JWT
2. Remove Redis/Redlock imports
3. Test multi-tab scenarios

### Phase 3: Optimize Client-Side

1. Remove SessionAutoRefresh if not needed
2. Or implement deduplication for long-lived pages
3. Update documentation

## Testing Checklist

- [ ] Single tab: Token refreshes before expiry
- [ ] Multiple tabs: No 400 errors on refresh
- [ ] Long session: 30-day refresh token works
- [ ] Failed refresh: Graceful degradation
- [ ] Protected routes: Still require authentication
- [ ] Feature flags: Still work as expected

## Configuration

### Environment Variables

```bash
# Required (same as before)
AUTHENTIK_CLIENT_ID=xxx
AUTHENTIK_CLIENT_SECRET=xxx
AUTHENTIK_ISSUER=https://auth.example.com/application/o/reflector/
AUTHENTIK_REFRESH_TOKEN_URL=https://auth.example.com/application/o/token/
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=xxx

# NOT Required anymore
# KV_URL=redis://... (removed)
```

### Docker Compose

```yaml
version: "3.8"

services:
  # No Redis needed!
  frontend:
    build: .
    ports:
      - "3000:3000"
    environment:
      - AUTHENTIK_CLIENT_ID=${AUTHENTIK_CLIENT_ID}
      - AUTHENTIK_CLIENT_SECRET=${AUTHENTIK_CLIENT_SECRET}
      # No KV_URL needed
```

## Security Considerations

1. **Refresh Token in JWT**: Encrypted with A256GCM, secure
2. **Cookie Security**: HttpOnly, Secure, SameSite flags
3. **Token Rotation**: Authentik handles rotation on refresh
4. **Expiry Handling**: Graceful degradation on refresh failure

## Conclusion

The middleware-based approach eliminates the multi-tab race condition without Redis by:

1. Moving refresh logic server-side (no broadcasting)
2. Handling each request independently (no race)
3. Updating cookies transparently (no client involvement)

This solution is simpler, more maintainable, and aligns with NextAuth's evolution toward server-side session management.
