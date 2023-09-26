import { useRef, useState } from "react";

type FinalSummaryProps = {
  text: string;
};

export default function FinalSummary(props: FinalSummaryProps) {
  const finalSummaryRef = useRef<HTMLParagraphElement>(null);
  const [isCopied, setIsCopied] = useState(false);

  const handleCopyClick = () => {
    let text_to_copy = finalSummaryRef.current?.innerText;

    text_to_copy &&
      navigator.clipboard.writeText(text_to_copy).then(() => {
        setIsCopied(true);
        // Reset the copied state after 2 seconds
        setTimeout(() => setIsCopied(false), 2000);
      });
  };

  return (
    <div className="overflow-y-auto h-auto max-h-full">
      <div className="flex flex-row justify-between items-center">
        <h2 className="text-xl md:text-2xl font-bold">Final Summary</h2>
        <button
          onClick={handleCopyClick}
          className={
            (isCopied ? "bg-blue-500" : "bg-blue-400") +
            " hover:bg-blue-500 focus-visible:bg-blue-500 text-white rounded p-2"
          }
          style={{ minHeight: "30px" }}
        >
          {isCopied ? "Copied!" : "Copy"}
        </button>
      </div>

      <p ref={finalSummaryRef}>{props.text}</p>
    </div>
  );
}
