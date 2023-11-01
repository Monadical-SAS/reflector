import { NextResponse, NextRequest } from "next/server";
import { get } from "@vercel/edge-config";

import { getFiefAuthMiddleware } from "./app/lib/fief";
import { getConfig } from "./app/lib/edgeConfig";

export async function middleware(request: NextRequest) {
  const domain = request.nextUrl.hostname;
  const config = await getConfig(domain);

  // Feature-flag protedted paths
  if (
    !config.features.browse &&
    request.nextUrl.pathname.startsWith("/browse")
  ) {
    return NextResponse.redirect(request.nextUrl.origin);
  }

  if (config.features.requireLogin) {
    const fiefMiddleware = await getFiefAuthMiddleware(request.nextUrl);
    const fiefResponse = fiefMiddleware(request);
    if (
      request.nextUrl.pathname == "/" ||
      request.nextUrl.pathname.startsWith("/transcripts") ||
      request.nextUrl.pathname.startsWith("/browse")
    ) {
      // return fiefAuthMiddleware(domain, config['auth_callback_url'])(request, {rewrite: request.nextUrl.origin + "/" + domain + request.nextUrl.pathname})
      const response = NextResponse.rewrite(
        request.nextUrl.origin + "/" + domain + request.nextUrl.pathname,
      );
      // response = (await fiefResponse).headers
      return response;
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

  return NextResponse.next();
}
