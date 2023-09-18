type FinalSummaryProps = {
  text: string;
};

export default function FinalSummary(props: FinalSummaryProps) {
  return (
    <div className="overflow-y-auto h-auto max-h-full">
      <h2 className="text-lg">Final Summary</h2>
      <p>{props.text}</p>
    </div>
  );
}
