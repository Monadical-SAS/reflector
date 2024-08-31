import { NextResponse, NextRequest } from "next/server";

import { getFiefAuthMiddleware } from "./app/lib/fief";
import { getConfig } from "./app/lib/edgeConfig";

export async function middleware(request: NextRequest) {
  const domain = request.nextUrl.hostname;
  const config = await getConfig(domain);

  if (
    request.nextUrl.pathname.match(
      "^/((?!api|_next/static|_next/image|favicon.ico).*)",
    )
  ) {
    // Feature-flag protedted paths
    if (
      (!config.features.browse &&
        request.nextUrl.pathname.startsWith("/browse")) ||
      (!config.features.rooms && request.nextUrl.pathname.startsWith("/rooms"))
    ) {
      return NextResponse.redirect(request.nextUrl.origin);
    }

    if (config.features.requireLogin) {
      const fiefMiddleware = await getFiefAuthMiddleware(request.nextUrl);
      const fiefResponse = await fiefMiddleware(request);
      return fiefResponse;
    }
  }

  return NextResponse.next();
}
