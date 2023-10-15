type LiveTranscriptionProps = {
  text: string;
  translateText: string;
};

export default function LiveTrancription(props: LiveTranscriptionProps) {
  return (
    <div className="text-center p-4">
      <p className="text-lg md:text-xl font-bold line-clamp-4">{props.text}</p>
      {props.translateText && (
        <p className="text-base md:text-lg font-bold line-clamp-4 mt-4">
          {props.translateText}
        </p>
      )}
    </div>
  );
}
