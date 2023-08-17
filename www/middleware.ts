import type { NextRequest } from "next/server";

import { fiefAuth } from "./app/lib/fief";

const authMiddleware = fiefAuth.middleware([
  {
    matcher: "/private",
    parameters: {},
  },
  {
    matcher: "/castles/:path*",
    parameters: {
      permissions: ["castles:read"],
    },
  },
]);

export async function middleware(request: NextRequest) {
  return authMiddleware(request);
}
