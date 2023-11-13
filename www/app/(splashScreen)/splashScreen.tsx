import { V1TranscriptsCreateRequest } from "../api/apis/DefaultApi";
import LeftSection from "./leftSection";
import RightSection from "./rightSection";

import { useState, useEffect } from "react";

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

enum DisplayedPage {
  LeftSection = "LEFT",
  RightSection = "RIGHT",
}

function SplashScreen(props: SplashScreen) {
  // Used for mobile only
  const [isMobile, setIsMobile] = useState(false);
  const [displayedPage, setDisplayedPage] = useState<DisplayedPage>(
    DisplayedPage.LeftSection,
  );

  useEffect(() => {
    const userAgent = navigator.userAgent;
    const mobile = /android|iPad|iPhone|iPod/.test(userAgent);
    setIsMobile(mobile);
  }, []);

  //         "flex flex-col items-center px-5 py-11 gap-0 md:gap-16 flex-auto self-stretch rounded-xl bg-blue-700 shadow-md" :

  return (
    <>
      <main
        className={
          "flex flex-1 flex-row p-3 items-start self-stretch rounded-lg"
        }
      >
        {(!isMobile || displayedPage == DisplayedPage.LeftSection) && (
          <section
            className={
              "gap-0 md:gap-4 flex flex-1 flex-col px-5 md:px-9 py-11 md:py-20 border items-start self-stretch rounded-xl bg-[#3158E2]"
            }
          >
            <LeftSection
              isMobile={isMobile}
              handlePageChange={() =>
                setDisplayedPage(DisplayedPage.RightSection)
              }
            />
          </section>
        )}

        {(!isMobile || displayedPage == DisplayedPage.RightSection) && (
          <section
            className={
              isMobile
                ? ""
                : "flex flex-1 flex-col items-left py-6 px-20 gap-6 self-stretch"
            }
          >
            <RightSection
              isMobile={isMobile}
              translationLanguage={props.translationLanguage}
              setTranslationLanguage={props.setTranslationLanguage}
              permissionDenied={props.permissionDenied}
              permissionOk={props.permissionOk}
              send={props.send}
              loadingSend={props.loadingSend}
              loading={props.loading}
              requestPermission={props.requestPermission}
            />
          </section>
        )}
      </main>
    </>
  );
}

export default SplashScreen;
