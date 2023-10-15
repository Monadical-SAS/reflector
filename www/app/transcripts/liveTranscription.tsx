type LiveTranscriptionProps = {
  text: string;
  translateText: string;
};

export default function LiveTrancription(props: LiveTranscriptionProps) {
  return (
    <div className="text-center p-4">
      <p
        className={`text-lg md:text-xl lg:text-2xl font-bold ${
          props.translateText ? "line-clamp-2 lg:line-clamp-5" : "line-clamp-4"
        }`}
      >
        {props.text}
      </p>
      {props.translateText && (
        <p className="text-base md:text-lg lg:text-xl font-bold line-clamp-2 lg:line-clamp-4 mt-4">
          {props.translateText}
        </p>
      )}
    </div>
  );
}
