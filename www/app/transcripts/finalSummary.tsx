type FinalSummaryProps = {
  text: string;
};

export default function FinalSummary(props: FinalSummaryProps) {
  return (
    <div className="mt-2 p-2 bg-white temp-transcription rounded">
      <h2>Final Summary</h2>
      <p>{props.text}</p>
    </div>
  );
}
