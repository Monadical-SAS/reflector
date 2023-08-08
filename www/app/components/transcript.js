import { useEffect, useState } from "react";
import axios from "axios";

const API_URL = process.env.NEXT_PUBLIC_API_URL;

const useCreateTranscript = () => {
  const [response, setResponse] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const createTranscript = () => {
    setLoading(true);
    const url = API_URL + "/v1/transcripts/";
    const data = {
      name: "Weekly All-Hands", // Hardcoded for now
    };

    console.log("Sending POST:", data);

    axios
      .post(url, data)
      .then((result) => {
        setResponse(result.data);
        setLoading(false);
        console.log("Response:", result.data);
      })
      .catch((err) => {
        setError(err.response || err);
        setLoading(false);
        alert("Error: " + (err.response || err));
        console.log("Error occurred:", err.response || err); // Debugging line
      });
  };

  // You can choose when to call createTranscript, e.g., based on some dependencies
  useEffect(() => {
    createTranscript();
  }, []); // Empty dependencies array means this effect will run once on mount

  return { response, loading, error, createTranscript };
};

export default useCreateTranscript;
