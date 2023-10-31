import { supportedLatinLanguages } from "../supportedLanguages";
import About from "./about";
import Privacy from "./privacy";
import SelectSearch from "react-select-search";
import { V1TranscriptsCreateRequest } from "../api/apis/DefaultApi";

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
  return (
    <>
      <div className="hidden lg:block"></div>
      <div className="lg:grid lg:grid-cols-2 lg:grid-rows-1 lg:gap-4 lg:h-full h-auto flex flex-col">
        <section className="flex flex-col items-center justify-center p-0 px-9 gap-6 flex-grow border rounded-md bg-[#3158E2]">
          <div className="flex flex-col max-w-xl items-left justify-center">
            <h1 className="self-stretch text-white text-[34px] font-poppins font-extrabold leading-normal pb-9">
              Welcome to reflector.media
            </h1>
            <p className="self-stretch text-white text-[15px] font-poppins font-normal leading-normal pb-4">
              Reflector is a transcription and summarization pipeline that
              transforms audio into knowledge.
            </p>
            <p className="self-stretch text-white text-[15px] font-poppins font-normal leading-normal pb-4">
              The output is meeting minutes and topic summaries enabling
              topic-specific analyses stored in your systems of record. This is
              accomplished on your infrastructure – without 3rd parties –
              keeping your data private, secure, and organized.
            </p>
            <About buttonText="Learn more" />
            <p className="self-stretch text-white text-[15px] font-poppins font-normal leading-normal pb-4">
              In order to use Reflector, we kindly request permission to access
              your microphone during meetings and events.
            </p>
            <Privacy buttonText="Privacy policy" />
          </div>
        </section>
        <section className="flex flex-col justify-center items-center w-full h-full">
          <div className="rounded-xl md:bg-blue-200 md:w-96 p-4 lg:p-6 flex flex-col mb-4 md:mb-10">
            <h2 className="text-2xl font-bold mt-2 mb-2"> Try Reflector</h2>
            <label className="mb-3">
              <p>Recording name</p>
              <div className="select-search-container">
                <input
                  className="select-search-input"
                  type="text"
                  onChange={props.handleNameChange}
                  placeholder="Optional"
                />
              </div>
            </label>

            <label className="mb-3">
              <p>Do you want to enable live translation?</p>
              <SelectSearch
                search
                options={supportedLatinLanguages}
                value={props.translationLanguage}
                onChange={(lang: any) => {
                  (!lang || typeof lang === "string") &&
                    props.setTranslationLanguage(lang);
                }}
                placeholder="Choose your language"
              />
            </label>

            {props.loading ? (
              <p className="">Checking permissions...</p>
            ) : props.permissionOk ? (
              <p className=""> Microphone permission granted </p>
            ) : props.permissionDenied ? (
              <p className="">
                Permission to use your microphone was denied, please change the
                permission setting in your browser and refresh this page.
              </p>
            ) : (
              <button
                className="mt-4 bg-blue-400 hover:bg-blue-500 focus-visible:bg-blue-500 text-white font-bold py-2 px-4 rounded"
                onClick={props.requestPermission}
                disabled={props.permissionDenied}
              >
                Request Microphone Permission
              </button>
            )}
            <button
              className="mt-4 bg-blue-400 hover:bg-blue-500 focus-visible:bg-blue-500 text-white font-bold py-2 px-4 rounded"
              onClick={props.send}
              disabled={!props.permissionOk || props.loadingSend}
            >
              {props.loadingSend ? "Loading..." : "Confirm"}
            </button>
          </div>
        </section>
      </div>
    </>
  );
}

export default SplashScreen;
