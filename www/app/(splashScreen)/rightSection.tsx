import Image from "next/image";
import { supportedLatinLanguages } from "../supportedLanguages";
import SelectSearch from "react-select-search";

type RightSection = {
  translationLanguage: string | undefined;
  setTranslationLanguage: (targetLanguage: string) => void;
  loading: boolean;
  requestPermission: () => void;
  permissionOk: boolean;
  permissionDenied: boolean;
  send: () => void;
  loadingSend: boolean;
  isMobile: boolean;
};

export default function RightSection(props: RightSection) {
  const displayMicText =
    props.loading || props.permissionOk || props.permissionDenied;

  return (
    <>
      <div
        className={
          "flex flex-col items-center justify-center self-stretch " +
          (props.isMobile ? "mb-10 mx-auto" : "")
        }
      >
        <Image src="/reach.png" width={87} height={87} alt="Reflector Logo" />
      </div>

      <div
        className={
          props.isMobile
            ? "flex flex-col items-center self-stretch p-8 rounded-lg bg-[#3158E2]"
            : "flex flex-col self-stretch"
        }
      >
        <h3 className="self-stretch text-[#0E1B48] text-3xl md:text-xl font-bold md:font-semibold leading-normal pt-0 pb-0 md:pb-6 text-white md:text-black mb-6 md:mb-0">
          Try Reflector
        </h3>

        <label
          htmlFor="recording-name"
          className="self-stretch text-black font-poppins text-base font-semibold leading-normal text-white md:text-black mb-2"
        >
          Recording Name
        </label>

        <input
          type="text"
          placeholder="Optional"
          name="recording-name"
          id="recording-name"
          className="flex h-12 items-center px-4 self-stretch rounded-md border border-black mb-4 hover:border-[#1e66f5] focus:outline-[#1e66f5]"
        />

        <label className="self-stretch text-black font-poppins text-base font-semibold leading-normal mb-2 text-white md:text-black">
          {props.isMobile
            ? "Enable live translation?"
            : "Do you want to enable live translation?"}
        </label>

        <div className="self-stretch">
          <SelectSearch
            search
            options={supportedLatinLanguages}
            value={props.translationLanguage}
            onChange={(lang: any) => {
              props.setTranslationLanguage(lang);
            }}
            placeholder="Choose your language"
          />
        </div>

        {displayMicText ? (
          <>
            {props.loading ? (
              <div className="flex items-center pr-2.5 mt-4  text-white md:text-black mb-2">
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
              <div className="flex items-center pr-2.5 mt-4 mb-2 text-white md:text-black">
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
              <p className="font-medium text-rose-600 mb-2">
                We're unable to access your microphone because permission has
                been declined. Please update your browser's permission settings
                to allow microphone access and then reload the page.
              </p>
            ) : (
              <></>
            )}
          </>
        ) : (
          <></>
        )}

        <div className="inline-block mt-2">
          {!displayMicText ? (
            <button
              className="hover:bg-[#B1CBFF] hover:text-black disabled:text-white inline-flex justify-center items-center px-4 py-1.5 gap-2.5 rounded bg-[#3158E2] text-white text-base font-poppins font-semibold mr-2"
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
            className={
              props.isMobile
                ? "flex justify-center items-center p-[6px_17px] gap-2.5 rounded-[4px] bg-[#B1CBFF] text-black px-4 py-1.5 text-[15px] font-semibold"
                : "hover:bg-[#B1CBFF] hover:text-black disabled:text-white inline-flex justify-center items-center px-4 py-1.5 gap-2.5 rounded bg-[#3158E2] text-white text-base font-poppins font-semibold"
            }
          >
            {props.loadingSend ? "Loading..." : "Start Recording"}
          </button>
        </div>
      </div>
    </>
  );
}
