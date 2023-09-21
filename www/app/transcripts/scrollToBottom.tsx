import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faArrowDown } from "@fortawesome/free-solid-svg-icons";

type ScrollToBottomProps = {
  visible: boolean;
  handleScrollBottom: () => void;
};

export default function ScrollToBottom(props: ScrollToBottomProps) {
  return (
    <div
      className={`absolute left-0 w-10 h-10 ${
        props.visible ? "flex" : "hidden"
      } top-[49%] text-2xl cursor-pointer opacity-70 hover:opacity-100 transition-opacity duration-200 animate-bounce rounded-xl text-blue-400`}
      onClick={() => {
        props.handleScrollBottom();
        return false;
      }}
    >
      <FontAwesomeIcon icon={faArrowDown} />
    </div>
  );
}
