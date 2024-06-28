import React from "react";
import Dropdown, { Option } from "react-dropdown";
import "react-dropdown/style.css";

const AudioInputsDropdown: React.FC<{
  audioDevices: Option[];
  disabled: boolean;
  hide: () => void;
  deviceId: string;
  setDeviceId: React.Dispatch<React.SetStateAction<string | null>>;
}> = (props) => {
  const handleDropdownChange = (option: Option) => {
    props.setDeviceId(option.value);
    props.hide();
  };

  return (
    <Dropdown
      options={props.audioDevices}
      onChange={handleDropdownChange}
      value={props.deviceId}
      className="flex-grow w-full"
      disabled={props.disabled}
    />
  );
};

export default AudioInputsDropdown;
