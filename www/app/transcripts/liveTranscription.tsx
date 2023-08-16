type LiveTranscriptionProps = {
  text: string;
};

export default function LiveTrancription(props: LiveTranscriptionProps) {
  return (
    <div className="h-[7svh] w-full bg-gray-800 text-white text-center py-4 text-2xl">
      &nbsp;{props.text}&nbsp;
    </div>
  );
}
