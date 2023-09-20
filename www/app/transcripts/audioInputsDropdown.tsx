import React, { useEffect, useState } from "react";
import Dropdown, { Option } from "react-dropdown";
import "react-dropdown/style.css";

const AudioInputsDropdown: React.FC<{
  audioDevices: Option[];
  disabled: boolean;
  hide: () => void;
  setDeviceId: React.Dispatch<React.SetStateAction<string | null>>;
}> = (props) => {
  const [ddOptions, setDdOptions] = useState<Option[]>([]);

  useEffect(() => {
    if (props.audioDevices) {
      setDdOptions(props.audioDevices);
      props.setDeviceId(
        props.audioDevices.length > 0 ? props.audioDevices[0].value : null,
      );
    }
  }, [props.audioDevices]);

  const handleDropdownChange = (option: Option) => {
    props.setDeviceId(option.value);
    props.hide();
  };

  return (
    <Dropdown
      options={ddOptions}
      onChange={handleDropdownChange}
      value={ddOptions[0]}
      className="flex-grow w-full"
      disabled={props.disabled}
    />
  );
};

export default AudioInputsDropdown;
