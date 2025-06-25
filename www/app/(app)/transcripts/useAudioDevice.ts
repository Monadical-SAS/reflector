import { useEffect, useState } from "react";

import { Option } from "react-dropdown";

const MIC_QUERY = { name: "microphone" as PermissionName };

const useAudioDevice = () => {
  const [permissionOk, setPermissionOk] = useState<boolean>(false);
  const [permissionDenied, setPermissionDenied] = useState<boolean>(false);
  const [audioDevices, setAudioDevices] = useState<Option[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // skips on SSR
    checkPermission();
  }, []);

  useEffect(() => {
    if (permissionOk) {
      updateDevices();
    }
  }, [permissionOk]);

  const checkPermission = (): void => {
    if (navigator.userAgent.includes("Firefox")) {
      navigator.mediaDevices
        .getUserMedia({ audio: true, video: false })
        .then((stream) => {
          setPermissionOk(true);
          setPermissionDenied(false);
        })
        .catch((e) => {
          setPermissionOk(false);
          setPermissionDenied(false);
        })
        .finally(() => setLoading(false));
      return;
    }

    navigator.permissions
      .query(MIC_QUERY)
      .then((permissionStatus) => {
        setPermissionOk(permissionStatus.state === "granted");
        setPermissionDenied(permissionStatus.state === "denied");
        permissionStatus.onchange = () => {
          setPermissionOk(permissionStatus.state === "granted");
          setPermissionDenied(permissionStatus.state === "denied");
        };
      })
      .catch(() => {
        setPermissionOk(false);
        setPermissionDenied(false);
      })
      .finally(() => {
        setLoading(false);
      });
  };

  const requestPermission = () => {
    navigator.mediaDevices
      .getUserMedia({
        audio: true,
      })
      .then((stream) => {
        if (!navigator.userAgent.includes("Firefox"))
          stream.getTracks().forEach((track) => track.stop());
        setPermissionOk(true);
      })
      .catch(() => {
        setPermissionDenied(true);
        setPermissionOk(false);
      })
      .finally(() => {
        setLoading(false);
      });
  };

  const getAudioStream = async (
    deviceId: string,
  ): Promise<MediaStream | null> => {
    try {
      const urlParams = new URLSearchParams(window.location.search);

      const noiseSuppression = urlParams.get("noiseSuppression") === "true";
      const echoCancellation = urlParams.get("echoCancellation") === "true";

      console.debug(
        "noiseSuppression",
        noiseSuppression,
        "echoCancellation",
        echoCancellation,
      );

      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          deviceId,
          noiseSuppression,
          echoCancellation,
        },
      });
      return stream;
    } catch (e) {
      setPermissionOk(false);
      setAudioDevices([]);
      return null;
    }
  };

  const updateDevices = async (): Promise<void> => {
    const devices = await navigator.mediaDevices.enumerateDevices();
    const _audioDevices = devices
      .filter(
        (d) => d.kind === "audioinput" && d.deviceId != "" && d.label != "",
      )
      .map((d) => ({ value: d.deviceId, label: d.label }));

    setPermissionOk(_audioDevices.length > 0);
    setAudioDevices(_audioDevices);
  };

  return {
    loading,
    permissionOk,
    permissionDenied,
    audioDevices,
    getAudioStream,
    requestPermission
  };
};

export default useAudioDevice;
