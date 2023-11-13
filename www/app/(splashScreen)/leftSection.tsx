import Image from "next/image";
import { useState } from "react";
import About from "./about";
import Privacy from "./privacy";

type LeftSection = {
  isMobile: boolean;
  handlePageChange: () => void;
};

export default function LeftSection(props: LeftSection) {
  const [modalContents, setModalContents] = useState<React.ReactNode | null>(
    null,
  );

  if (modalContents) {
    return (
      <>
        <button
          className="hover:bg-[#0E1B48] hover:text-white disabled:text-black flex gap-2.5 px-4 py-1.5 rounded bg-[var(--Light-Blue,#B1CBFF)]  justify-start"
          onClick={() => setModalContents(null)}
        >
          Back
        </button>
        {modalContents}
      </>
    );
  }

  return (
    <>
      <h1 className="text-white md:text-4xl text-2xl font-extrabold mb-8">
        Welcome to Reflector!
      </h1>

      {props.isMobile && (
        <button
          className="flex-1 w-full px-4 py-1.5 mb-8 justify-center items-center gap-2.5 rounded bg-[#B1CBFF] text-black hover:bg-[#0E1B48] hover:text-white font-semibold"
          onClick={() => props.handlePageChange()}
        >
          Try Reflector
        </button>
      )}

      <p className="text-white mb-4 md:mb-0">
        Reflector is a transcription and summarization pipeline that transforms
        audio into knowledge.
      </p>
      <p className="text-white mb-2 md:mb-0">
        The output is meeting minutes and topic summaries enabling
        topic-specific analyses stored in your systems of record. This is
        accomplished on your infrastructure, without 3rd parties, keeping your
        data private, secure, and organized.
      </p>
      <p className="text-white  mb-4 md:mb-0">
        <a
          className="text-white cursor-pointer underline font-semibold hover:no-underline"
          onClick={() => setModalContents(<About />)}
        >
          Learn More
        </a>
      </p>

      <p className="text-white mb-2 md:mb-0">
        In order to use Reflector, we need microphone permissions to access the
        audio during meetings and events.
      </p>
      <p className="text-white mb-8 md:mb-0">
        <a
          className="text-white cursor-pointer underline font-semibold hover:no-underline"
          onClick={() => setModalContents(<Privacy />)}
        >
          Privacy Policy
        </a>
      </p>

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
  );
}
