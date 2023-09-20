import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faMicrophone } from "@fortawesome/free-solid-svg-icons";
import React, { useEffect, useState } from "react";
import Dropdown, { Option } from "react-dropdown";
import "react-dropdown/style.css";

const AudioInputsDropdown: React.FC<{
  audioDevices: Option[];
  disabled: boolean;
  setDeviceId: React.Dispatch<React.SetStateAction<string | null>>;
}> = ({ audioDevices, disabled, setDeviceId }) => {
  const [ddOptions, setDdOptions] = useState<Option[]>([]);

  useEffect(() => {
    if (audioDevices) {
      setDdOptions(audioDevices);
      setDeviceId(audioDevices.length > 0 ? audioDevices[0].value : null);
    }
  }, [audioDevices]);

  const handleDropdownChange = (option: Option) => {
    setDeviceId(option.value);
  };

  if (audioDevices?.length > 0) {
    return (
      <div className="flex w-full items-center">
        <FontAwesomeIcon icon={faMicrophone} className="p-2" />
        <Dropdown
          options={ddOptions}
          onChange={handleDropdownChange}
          value={ddOptions[0]}
          className="flex-grow"
          disabled={disabled}
        />
      </div>
    );
  }
  return null;
};

export default AudioInputsDropdown;
