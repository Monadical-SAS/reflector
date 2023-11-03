import { supportedLatinLanguages } from "../supportedLanguages";
import About from "./about";
import Privacy from "./privacy";
import SelectSearch from "react-select-search";
import { V1TranscriptsCreateRequest } from "../api/apis/DefaultApi";
import Image from "next/image";

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
  return (
    <>
      <div className="hidden lg:block"></div>
      <div className="lg:grid lg:grid-cols-2 lg:grid-rows-1 lg:gap-4 lg:h-full h-auto flex flex-col">
        <section className="flex flex-col items-center justify-center p-8 px-9 gap-6 flex-1 border rounded-md bg-[#3158E2]">
          <div className="flex flex-col max-w-xl items-left justify-center">
            <h1 className="self-stretch text-white text-4xl font-poppins font-extrabold leading-normal pb-9">
              Welcome to Reflector!
            </h1>
            <p className="self-stretch text-white text-[15px] font-poppins font-normal leading-normal pb-4">
              Reflector is a transcription and summarization pipeline that
              transforms audio into knowledge.
            </p>
            <p className="self-stretch text-white text-[15px] font-poppins font-normal leading-normal pb-4">
              The output is meeting minutes and topic summaries enabling
              topic-specific analyses stored in your systems of record. This is
              accomplished on your infrastructure, without 3rd parties, keeping
              your data private, secure, and organized.
            </p>
            <About buttonText="Learn more" />
            <p className="self-stretch text-white text-[15px] font-poppins font-normal leading-normal pb-4">
              In order to use Reflector, we need microphone permissions to
              access the audio during meetings and events.
            </p>
            <Privacy buttonText="Privacy policy" />

            <div className="mx-auto">
              <Image
                src="/waveform.png"
                width={403}
                height={102}
                alt="Reflector Logo"
              />
            </div>
          </div>
        </section>
        <section className="flex flex-col justify-center gap-1 flex-1 self-stretch p-8">
          <div className="flex flex-col items-center justify-center self-stretch">
            <Image
              src="/reach-logo.png"
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
                <>
                  Permission to use your microphone was denied, please change
                  the permission setting in your browser and refresh this page.
                </>
              ) : (
                <></>
              )}
            </>
          ) : (
            <button
              className="blue-button"
              onClick={props.requestPermission}
              disabled={props.permissionDenied}
            >
              Request Microphone Permission
            </button>
          )}

          <div className="inline-block mt-4">
            <button
              onClick={props.send}
              disabled={!props.permissionOk || props.loadingSend}
              className="inline-flex justify-center items-center px-4 py-1.5 gap-2.5 rounded bg-[#3158E2] text-white text-base font-poppins font-semibold"
            >
              {props.loadingSend ? "Loading..." : "Start new recording"}
            </button>
          </div>
        </section>
      </div>
    </>
  );
}

export default SplashScreen;
