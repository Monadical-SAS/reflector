import { useEffect, useState } from "react";
import Peer from "simple-peer";

const WebRTC_SERVER_URL = "http://127.0.0.1:1250/offer"

const useWebRTC = (stream) => {
  const [data, setData] = useState(null);

  useEffect(() => {
    let peer = new Peer({ initiator: true, stream: stream });

    peer.on("signal", (data) => {
      // This is where you'd send the signal data to the server.
      // The server would then send it back to other peers who would then
      // use `peer.signal()` method to continue the connection negotiation.
      if ('sdp' in data) {
        fetch(WebRTC_SERVER_URL, {
          body: JSON.stringify({
            sdp: data.sdp,
            type: data.type,
          }),
          headers: {
            'Content-Type': 'application/json'
          },
          method: 'POST'
        }).then(function (response) {
          return response.json();
        }).then(function (answer) {
          return peer.signal(answer);
        }).catch(function (e) {
          alert(e);
        });
      }
    });

    peer.on("connect", () => {
      console.log("WebRTC connected");
    });

    peer.on("data", (data) => {
      // Received data from the server.
      console.log(data.toString())
      const serverData = JSON.parse(data.toString());
      setData(serverData);
    });

    // Clean up
    return () => {
      peer.destroy();
    };
  }, [stream]);

  return data;
};

export default useWebRTC;
