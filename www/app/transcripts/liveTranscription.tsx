type LiveTranscriptionProps = {
  text: string;
  translateText: string;
};

export default function LiveTrancription(props: LiveTranscriptionProps) {
  return (
    <div className="text-center p-4">
      <p className="text-lg md:text-xl font-bold line-clamp-4">
        {props.translateText ? props.translateText : props.text}
      </p>
      {props.translateText && (
        <p className="text-base md:textlg font-bold line-clamp-4">
          {props.text}
        </p>
      )}
    </div>
  );
}
