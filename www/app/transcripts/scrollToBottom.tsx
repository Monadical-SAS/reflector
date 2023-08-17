type ScrollToBottomProps = {
  visible: boolean;
  hasFinalSummary: boolean;
  handleScrollBottom: () => void;
};

export default function ScrollToBottom(props: ScrollToBottomProps) {
  return (
    <div
      className={`absolute right-5 w-10 h-10 ${
        props.visible ? "flex" : "hidden"
      } ${
        props.hasFinalSummary ? "top-[49%]" : "bottom-1"
      } justify-center items-center text-2xl cursor-pointer opacity-70 hover:opacity-100 transition-opacity duration-200 animate-bounce rounded-xl border-slate-400 bg-[#3c82f638] text-[#3c82f6ed]`}
      onClick={() => {
        props.handleScrollBottom();
        return false;
      }}
    >
      &#11015;
    </div>
  );
}
