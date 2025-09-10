import { withAuth } from "next-auth/middleware";
import { getConfig } from "./app/lib/config";
import { NextResponse } from "next/server";
import { PROTECTED_PAGES } from "./app/lib/auth";

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
