import { NextResponse, NextRequest } from "next/server";
import { get } from "@vercel/edge-config";

import { getFiefAuthMiddleware } from "./app/lib/fief";
import { getConfig } from "./app/lib/edgeConfig";

export async function middleware(request: NextRequest) {
  const domain = request.nextUrl.hostname;
  const config = await getConfig(domain);

  if (
    request.nextUrl.pathname.match(
      "/((?!api|_next/static|_next/image|favicon.ico).*)",
    )
  ) {
    // Feature-flag protedted paths
    if (
      !config.features.browse &&
      request.nextUrl.pathname.startsWith("/browse")
    ) {
      return NextResponse.redirect(request.nextUrl.origin);
    }

    if (config.features.requireLogin) {
      const fiefMiddleware = await getFiefAuthMiddleware(request.nextUrl);
      const fiefResponse = await fiefMiddleware(request);

      if (
        request.nextUrl.pathname == "/" ||
        request.nextUrl.pathname.startsWith("/transcripts") ||
        request.nextUrl.pathname.startsWith("/browse")
      ) {
        if (!fiefResponse.headers.get("x-middleware-rewrite")) {
          fiefResponse.headers.set(
            "x-middleware-rewrite",
            request.nextUrl.origin + "/" + domain + request.nextUrl.pathname,
          );
        }
      }
      return fiefResponse;
    }

    if (
      request.nextUrl.pathname == "/" ||
      request.nextUrl.pathname.startsWith("/transcripts") ||
      request.nextUrl.pathname.startsWith("/browse")
    ) {
      return NextResponse.rewrite(
        request.nextUrl.origin + "/" + domain + request.nextUrl.pathname,
      );
    }
  }

  return NextResponse.next();
}
