import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faClose } from "@fortawesome/free-solid-svg-icons";
import { MouseEventHandler } from "react";

type ModalProps = {
  children: JSX.Element;
  close: () => void;
};
const cancelClick: MouseEventHandler<HTMLDivElement> = (event) => {
  event.preventDefault();
  event.stopPropagation();
};

export default function FullscreenModal(props: ModalProps) {
  return (
    <div
      className="fixed z-50 cursor-pointer top-0 bottom-0 left-0 right-0 flex justify-center items-center bg-black/10"
      onClick={props.close}
    >
      <div className="p-3 md:p-5 bg-white rounded-lg border-blue-300 h:auto max-w-[90svw] w-auto md:max-w-[80svw] relative pt-4">
        <button
          className="absolute right-2 top-2 p-0 min-h-0"
          onClick={props.close}
        >
          <FontAwesomeIcon icon={faClose} />
        </button>
        <div
          className="h-auto md:max-h-[75svh] max-h-[80svh] overflow-auto px-2 cursor-default text-left"
          onClick={cancelClick}
        >
          {props.children}
        </div>
      </div>
    </div>
  );
}
