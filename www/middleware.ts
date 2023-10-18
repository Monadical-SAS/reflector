import type { NextRequest } from "next/server";

import { fiefAuth } from "./app/lib/fief";

let protectedPath: any = [];
if (process.env.NEXT_PUBLIC_FEAT_LOGIN_REQUIRED === "1") {
  protectedPath = [
    {
      matcher: "/transcripts/((?!new).*)",
      parameters: {},
    },
    {
      matcher: "/browse",
      parameters: {},
    },
  ];
}

const authMiddleware = fiefAuth.middleware(protectedPath);
export async function middleware(request: NextRequest) {
  return authMiddleware(request);
}
