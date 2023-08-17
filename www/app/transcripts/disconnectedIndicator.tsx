import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faLinkSlash } from "@fortawesome/free-solid-svg-icons";

export default function DisconnectedIndicator() {
  return (
    <div className="absolute top-0 left-0 w-full h-full bg-black opacity-50 flex justify-center items-center">
      <div className="text-white text-2xl">
        <FontAwesomeIcon icon={faLinkSlash} className="mr-2" />
        Disconnected
      </div>
    </div>
  );
}
