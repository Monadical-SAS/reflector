import { useEffect, useState } from "react";
import { components } from "../reflector-api";

export const useWhereby = () => {
  const [wherebyLoaded, setWherebyLoaded] = useState(false);
  useEffect(() => {
    if (typeof window !== "undefined") {
      import("@whereby.com/browser-sdk/embed")
        .then(() => {
          setWherebyLoaded(true);
        })
        .catch(console.error.bind(console));
    }
  }, []);
  return wherebyLoaded;
};

export const getWherebyUrl = (
  meeting: Pick<components["schemas"]["Meeting"], "room_url" | "host_room_url">,
) =>
  // host_room_url possible '' atm
  meeting.host_room_url || meeting.room_url;
