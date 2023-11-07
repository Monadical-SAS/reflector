import { supportedLatinLanguages } from "../supportedLanguages";
import About from "./about";
import Privacy from "./privacy";
import SelectSearch from "react-select-search";
import { V1TranscriptsCreateRequest } from "../api/apis/DefaultApi";
import Image from "next/image";
import { useState } from "react";

type SplashScreen = {
  handleNameChange: React.ChangeEventHandler<HTMLInputElement>;
  loading: boolean;
  requestPermission: () => void;
  permissionOk: boolean;
  permissionDenied: boolean;
  createTranscriptLoading: boolean;
  create: (params: V1TranscriptsCreateRequest["createTranscript"]) => void;
  translationLanguage: string | undefined;
  setTranslationLanguage: (targetLanguage: string) => void;
  send: () => void;
  loadingSend: boolean;
};

function SplashScreen(props: SplashScreen) {
  const displayMicText =
    props.loading || props.permissionOk || props.permissionDenied;

  const [modalContents, setModalContents] = useState<React.ReactNode | null>(
    null,
  );

  return (
    <>
      <main className="flex flex-1 flex-row p-3 items-start self-stretch rounded-lg">
        <section className="gap-4 flex flex-1 flex-col p-9 border rounded-md items-start justify-center self-stretch rounded-xl bg-[#3158E2]">
          {modalContents ? (
            <>
              <button
                className="flex gap-2.5 px-4 py-1.5 rounded bg-[var(--Light-Blue,#B1CBFF)]  justify-start"
                onClick={() => setModalContents(null)}
              >
                Back
              </button>
              {modalContents}
            </>
          ) : (
            <>
              <h1 className="text-white text-4xl font-extrabold mb-8">
                Welcome to Reflector!
              </h1>
              <p className="text-white">
                Reflector is a transcription and summarization pipeline that
                transforms audio into knowledge.
              </p>
              <p className="text-white">
                The output is meeting minutes and topic summaries enabling
                topic-specific analyses stored in your systems of record. This
                is accomplished on your infrastructure, without 3rd parties,
                keeping your data private, secure, and organized.
              </p>
              <a
                className="text-white cursor-pointer underline font-semibold hover:no-underline mb-8"
                onClick={() => setModalContents(<About />)}
              >
                Learn More
              </a>

              <p className="text-white">
                In order to use Reflector, we need microphone permissions to
                access the audio during meetings and events.
              </p>
              <a
                className="text-white cursor-pointer underline font-semibold hover:no-underline mb-8"
                onClick={() => setModalContents(<Privacy />)}
              >
                Privacy Policy
              </a>

              <Image
                alt="Reflector Logo"
                loading="lazy"
                width="403"
                height="102"
                decoding="async"
                data-nimg="1"
                src="/waveform.png"
                style={{ color: "transparent", width: "100%", height: "102px" }}
              />
            </>
          )}
        </section>

        {/* Right side */}

        <section
          className="flex flex-1 flex-col items-left justify-center p-9"
          style={{
            padding: "86px 24px",
            gap: "25px",
            alignSelf: "stretch",
          }}
        >
          <div className="flex flex-col items-center justify-center self-stretch">
            <Image
              src="/reach.png"
              width={87}
              height={87}
              alt="Reflector Logo"
            />
          </div>

          <h3 className="self-stretch text-[#0E1B48] font-poppins text-xl font-semibold leading-normal pt-0 pb-6">
            Try Reflector
          </h3>

          <label
            htmlFor="recording-name"
            className="self-stretch text-black font-poppins text-base font-semibold leading-normal"
          >
            Recording Name
          </label>

          <input
            type="text"
            placeholder="Optional"
            name="recording-name"
            id="recording-name"
            className="flex h-12 items-center px-4 self-stretch rounded-md border border-black mb-4"
          />

          <label className="self-stretch text-black font-poppins text-base font-semibold leading-normal">
            Do you want to enable Live Translation?
          </label>
          <SelectSearch
            search
            options={supportedLatinLanguages}
            value={props.translationLanguage}
            onChange={(lang: any) => {
              props.setTranslationLanguage(lang);
            }}
            placeholder="Choose your language"
          />

          {displayMicText ? (
            <>
              {props.loading ? (
                <div className="flex items-center pr-2.5 mt-4">
                  <Image
                    src="/microphone.png"
                    width={11}
                    height={17}
                    alt="Microphone"
                    className="mr-2"
                  />
                  Checking permissions&dots;
                </div>
              ) : props.permissionOk ? (
                <div className="flex items-center pr-2.5 mt-4">
                  <Image
                    src="/microphone.png"
                    width={11}
                    height={17}
                    alt="Microphone"
                    className="mr-2"
                  />
                  Microphone permission granted
                </div>
              ) : props.permissionDenied ? (
                <p className="font-medium text-rose-600">
                  We're unable to access your microphone because permission has
                  been declined. Please update your browser's permission
                  settings to allow microphone access and then reload the page.
                </p>
              ) : (
                <></>
              )}
            </>
          ) : (
            <></>
          )}

          <div className="inline-block">
            {!displayMicText ? (
              <button
                className="inline-flex justify-center items-center px-4 py-1.5 gap-2.5 rounded bg-[#3158E2] text-white text-base font-poppins font-semibold mr-2"
                onClick={props.requestPermission}
                disabled={props.permissionDenied}
              >
                Request Permissions
              </button>
            ) : (
              <></>
            )}

            <button
              onClick={props.send}
              disabled={!props.permissionOk || props.loadingSend}
              className="inline-flex justify-center items-center px-4 py-1.5 gap-2.5 rounded bg-[#3158E2] text-white text-base font-poppins font-semibold"
            >
              {props.loadingSend ? "Loading..." : "Start Recording"}
            </button>
          </div>
        </section>
      </main>
    </>
  );
}

export default SplashScreen;
