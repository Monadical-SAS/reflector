type LiveTranscriptionProps = {
  text: string;
};

export default function LiveTrancription(props: LiveTranscriptionProps) {
  return (
    <div className="text-center p-4">
      <p className="text-lg md:text-xl font-bold">
        {/* Nous allons prendre quelques appels téléphoniques et répondre à quelques questions */}
        {props.text}
      </p>
    </div>
  );
}
