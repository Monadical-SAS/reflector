import { withAuth } from "next-auth/middleware";
import { getConfig } from "./app/lib/edgeConfig";
import { NextResponse } from "next/server";

const LOGIN_REQUIRED_PAGES = [
  "/transcripts/[!new]",
  "/browse(.*)",
  "/rooms(.*)",
];

const PROTECTED_PAGES = new RegExp(
  LOGIN_REQUIRED_PAGES.map((page) => `^${page}$`).join("|"),
);

export const config = {
  matcher: [
    "/((?!api|_next/static|_next/image|favicon.ico|sitemap.xml|robots.txt).*)",

    // must be a copy of LOGIN_REQUIRED_PAGES
    // cannot use anything dynamic (...LOGIN_REQUIRED_PAGES, or .concat(LOGIN_REQUIRED_PAGES))
    // as per https://nextjs.org/docs/messages/invalid-page-config
    "/",
    "/transcripts(.*)",
    "/browse(.*)",
    "/rooms(.*)",
  ],
};

export default withAuth(
  async function middleware(request) {
    const config = await getConfig();
    const pathname = request.nextUrl.pathname;

    // feature-flags protected paths
    if (
      (!config.features.browse && pathname.startsWith("/browse")) ||
      (!config.features.rooms && pathname.startsWith("/rooms"))
    ) {
      return NextResponse.redirect(request.nextUrl.origin);
    }
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

/**

import { NextResponse, NextRequest } from "next/server";

// import { getFiefAuthMiddleware } from "./app/lib/fief";
import { getToken } from "next-auth/jwt";
import { getConfig } from "./app/lib/edgeConfig";
import { authOptions } from "./app/api/auth/[...nextauth]/route";


export async function middleware(request: NextRequest) {
  const config = await getConfig();

  console.log(
    "---------------------------------------------------------------",
  );
  console.log(
    "middleware",
    "request.nextUrl.pathname",
    request.nextUrl.pathname,
  );
  console.log("middleware", "config", config);

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
      console.log("!! redirecting to", request.nextUrl.origin);
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
**/
