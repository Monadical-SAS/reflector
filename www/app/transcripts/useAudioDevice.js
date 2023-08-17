import { useEffect, useState } from "react";

const useAudioDevice = () => {
  const [permissionOk, setPermissionOk] = useState(false);
  const [audioDevices, setAudioDevices] = useState([]);
  const [loading, setLoading] = useState(true);

  const requestPermission = () => {
    navigator.mediaDevices
      .getUserMedia({
        audio: true,
      })
      .then(() => {
        setPermissionOk(true);
        updateDevices();
      })
      .catch(() => {
        setPermissionOk(false);
      })
      .finally(() => {
        setLoading(false);
      });
  };

  const getAudioStream = async (deviceId) => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          deviceId,
          noiseSuppression: false,
          echoCancellation: false,
        },
      });
      return stream;
    } catch (e) {
      setPermissionOk(false);
      setAudioDevices([]);
      return null;
    }
  };

  const updateDevices = async () => {
    const devices = await navigator.mediaDevices.enumerateDevices();
    const _audioDevices = devices
      .filter(
        (d) => d.kind === "audioinput" && d.deviceId != "" && d.label != "",
      )
      .map((d) => ({ value: d.deviceId, label: d.label }));

    setPermissionOk(_audioDevices.length > 0);
    setAudioDevices(_audioDevices);
  };

  useEffect(() => {
    requestPermission();
  }, []);

  return {
    permissionOk,
    audioDevices,
    getAudioStream,
    requestPermission,
    loading,
  };
};

export default useAudioDevice;
