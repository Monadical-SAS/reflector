import { useEffect, useState } from "react";

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
