import { faSpinner } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";

export default () => (
  <div className="flex flex-grow items-center justify-center h-20">
    <FontAwesomeIcon
      icon={faSpinner}
      className="animate-spin-slow text-gray-600 flex-grow rounded-lg md:rounded-xl h-10 w-10"
    />
  </div>
);
