import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faArrowDown } from "@fortawesome/free-solid-svg-icons";

type ScrollToBottomProps = {
  visible: boolean;
  handleScrollBottom: () => void;
};

export default function ScrollToBottom(props: ScrollToBottomProps) {
  return (
    <div
      className={`absolute bottom-0 right-0 ${
        props.visible ? "flex" : "hidden"
      }  text-2xl cursor-pointer opacity-70 hover:opacity-100 transition-opacity duration-200 text-blue-400`}
      onClick={() => {
        props.handleScrollBottom();
        return false;
      }}
    >
      <FontAwesomeIcon icon={faArrowDown} className="animate-bounce" />
    </div>
  );
}
