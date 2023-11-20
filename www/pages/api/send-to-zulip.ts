import { NextApiRequest, NextApiResponse } from "next";
import axios from "axios";

type ZulipStream = {
  id: number;
  name: string;
  topics: string[];
};

async function getTopics(stream_id: number): Promise<string[]> {
  try {
    const response = await axios.get(
      `https://${process.env.ZULIP_REALM}/api/v1/users/me/${stream_id}/topics`,
      {
        auth: {
          username: process.env.ZULIP_BOT_EMAIL || "?",
          password: process.env.ZULIP_API_KEY || "?",
        },
      },
    );
    return response.data.topics.map((topic) => topic.name);
  } catch (error) {
    console.error("Error fetching topics for stream " + stream_id, error);
    throw error; // Propagate the error up to be handled by the caller
  }
}

async function getStreams(): Promise<ZulipStream[]> {
  try {
    const response = await axios.get(
      `https://${process.env.ZULIP_REALM}/api/v1/streams`,
      {
        auth: {
          username: process.env.ZULIP_BOT_EMAIL || "?",
          password: process.env.ZULIP_API_KEY || "?",
        },
      },
    );

    const streams: ZulipStream[] = [];
    for (const stream of response.data.streams) {
      console.log("Loading topics for " + stream.name);
      const topics = await getTopics(stream.stream_id);
      streams.push({ id: stream.stream_id, name: stream.name, topics });
    }

    return streams;
  } catch (error) {
    console.error("Error fetching zulip streams", error);
    throw error; // Propagate the error up
  }
}

export default async (req: NextApiRequest, res: NextApiResponse) => {
  try {
    const streams = await getStreams();
    return res.status(200).json({ streams });
  } catch (error) {
    // Handle errors more gracefully
    return res.status(500).json({ error: "Internal Server Error" });
  }
};
