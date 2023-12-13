export type TimeSlice = {
  start: number;
  end: number;
};

export type SelectedText = number | TimeSlice | undefined;

export function selectedTextIsSpeaker(
  selectedText: SelectedText,
): selectedText is number {
  return typeof selectedText == "number";
}
export function selectedTextIsTimeSlice(
  selectedText: SelectedText,
): selectedText is TimeSlice {
  return (
    typeof (selectedText as any)?.start == "number" &&
    typeof (selectedText as any)?.end == "number"
  );
}
