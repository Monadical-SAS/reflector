import { NextApiRequest } from "next";
import { fief, getFiefAuth } from "../../lib/fief";
// type FiefNextApiHandler<T> = (req: NextApiRequest & AuthenticateRequestResult, res: NextApiResponse<T>) => unknown | Promise<unknown>;

export default (req: any, res) => {
  const domain = req.url;
  console.log("user", req.url, getFiefAuth("localhost").currentUser());
  return getFiefAuth("localhost").currentUser()(req, res);
};
// export default fief.currentUser()
