import { getFiefAuth } from "../../app/lib/fief";
import { NextApiRequest, NextApiResponse } from "next";

export default async (req: NextApiRequest, res: NextApiResponse<any>) => {
  const fromUrl = req.headers["referer"] && new URL(req.headers["referer"]);
  const fief = fromUrl && (await getFiefAuth(fromUrl));
  if (fief) {
    return fief.currentUser()(req as any, res as any);
  } else {
    return res.status(200).json({ userinfo: null, access_token_info: null });
  }
};
