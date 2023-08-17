type FinalSummaryProps = {
  text: string;
};

export default function FinalSummary(props: FinalSummaryProps) {
  return (
    <div className="min-h-[200px] overflow-y-auto mt-2 p-2 bg-white temp-transcription rounded">
      <h2>Final Summary</h2>
      <p>{props.text}</p>
    </div>
  );
}
