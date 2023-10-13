"use client";
import React, { useEffect, useState } from "react";
import useWebRTC from "../useWebRTC";
import useTranscript from "../useTranscript";
import { useWebSockets } from "../useWebSockets";
import useAudioDevice from "../useAudioDevice";
import "../../styles/button.css";
import { Topic } from "../webSocketTypes";
import getApi from "../../lib/getApi";
import About from "../../(aboutAndPrivacy)/about";
import Privacy from "../../(aboutAndPrivacy)/privacy";
import { lockWakeState, releaseWakeState } from "../../lib/wakeLock";
import { useRouter } from "next/navigation";
import createTranscript from "../createTranscript";
import { GetTranscript } from "../../api";
import { Router } from "next/router";
import useCreateTranscript from "../createTranscript";

const TranscriptCreate = () => {
  // const transcript = useTranscript(stream, api);
  const router = useRouter();
  const api = getApi();

  const [name, setName] = useState<string>();
  const nameChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setName(event.target.value);
  };
  const [targetLanguage, setTargetLanguage] = useState<string>();

  const createTranscript = useCreateTranscript();

  const send = () => {
    if (createTranscript.loading || permissionDenied) return;
    createTranscript.create({ name, targetLanguage });
  };
  useEffect(() => {
    createTranscript.response &&
      router.push(`/transcripts/${createTranscript.response.id}/record`);
  }, [createTranscript.response]);

  const {
    loading,
    permissionOk,
    permissionDenied,
    audioDevices,
    requestPermission,
    getAudioStream,
  } = useAudioDevice();

  return (
    <>
      <div></div>
      <div className="max-h-full overflow-auto">
        <section className="flex flex-col w-full h-full items-center justify-evenly p-4 md:px-6 md:py-8">
          <div>
            <div className="flex flex-col max-w-xl items-center justify-center">
              <h1 className="text-2xl font-bold mb-2">
                Welcome to reflector.media
              </h1>
              <p>
                Reflector is a transcription and summarization pipeline that
                transforms audio into knowledge. The output is meeting minutes
                and topic summaries enabling topic-specific analyses stored in
                your systems of record. This is accomplished on your
                infrastructure – without 3rd parties – keeping your data
                private, secure, and organized.
              </p>
              <About buttonText="Learn more" />
              <input type="text" onChange={nameChange} />
              <button onClick={() => setTargetLanguage("fr")}>Language</button>
              <h2 className="text-2xl font-bold mt-4 mb-2">
                Audio Permissions
              </h2>
              {loading ? (
                <p className="text-center">Checking permission...</p>
              ) : permissionOk ? (
                <> Microphone permission granted </>
              ) : (
                <>
                  <p className="text-center">
                    In order to use Reflector, we kindly request permission to
                    access your microphone during meetings and events.
                    <br />
                    <Privacy buttonText="Privacy policy" />
                    <br />
                    {permissionDenied
                      ? "Permission to use your microphone was denied, please change the permission setting in your browser and refresh this page."
                      : "Please grant permission to continue."}
                  </p>
                  <button
                    className="mt-4 bg-blue-400 hover:bg-blue-500 focus-visible:bg-blue-500 text-white font-bold py-2 px-4 rounded m-auto"
                    onClick={requestPermission}
                    disabled={permissionDenied}
                  >
                    {permissionDenied ? "Access denied" : "Grant Permission"}
                  </button>
                </>
              )}
            </div>
            <button onClick={send} disabled={!permissionOk}>
              {createTranscript.loading ? "loading" : "Send"}
            </button>
          </div>
        </section>
      </div>
    </>
  );
};

export default TranscriptCreate;
