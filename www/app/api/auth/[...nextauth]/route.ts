// NextAuth route handler for Authentik
// Refresh rotation has been taken from https://next-auth.js.org/v3/tutorials/refresh-token-rotation even if we are using 4.x

import NextAuth from "next-auth";
import { authOptions } from "../../../lib/auth";

const handler = NextAuth(authOptions);

export { handler as GET, handler as POST };
