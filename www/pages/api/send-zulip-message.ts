import axios from "axios";
import { URLSearchParams } from "url";

export default async function handler(req, res) {
  if (req.method === "POST") {
    const { stream, topic, message } = req.body;
    console.log("Sending zulip message", stream, topic);

    if (!stream || !topic || !message) {
      return res.status(400).json({ error: "Missing required parameters" });
    }

    try {
      // Construct URL-encoded data
      const params = new URLSearchParams();
      params.append("type", "stream");
      params.append("to", stream);
      params.append("topic", topic);
      params.append("content", message);

      // Send the request1
      const zulipResponse = await axios.post(
        `https://${process.env.ZULIP_REALM}/api/v1/messages`,
        params,
        {
          auth: {
            username: process.env.ZULIP_BOT_EMAIL || "?",
            password: process.env.ZULIP_API_KEY || "?",
          },
          headers: {
            "Content-Type": "application/x-www-form-urlencoded",
          },
        },
      );

      return res.status(200).json(zulipResponse.data);
    } catch (error) {
      return res.status(500).json({ failed: true, error: error });
    }
  } else {
    res.setHeader("Allow", ["POST"]);
    res.status(405).end(`Method ${req.method} Not Allowed`);
  }
}
