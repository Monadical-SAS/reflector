import { useEffect, useState } from 'react';
import Peer from 'simple-peer';

const useWebRTC = (stream) => {
    const [data, setData] = useState(null);

    useEffect(() => {
        let peer = new Peer({ initiator: true, stream: stream });

        peer.on('signal', data => {
            // This is where you'd send the signal data to the server.
            // The server would then send it back to other peers who would then
            // use `peer.signal()` method to continue the connection negotiation.
            console.log('signal', data);
        });

        peer.on('connect', () => {
            console.log('WebRTC connected');
        });

        peer.on('data', data => {
            // Received data from the server.
            const serverData = JSON.parse(data.toString());
            setData(serverData);
        });

        // Clean up
        return () => {
            peer.destroy();
        }
    }, [stream]);

    return data;
};

export default useWebRTC;
