import React, { useRef, useEffect, useState } from "react";

import Dropdown, { Option } from "react-dropdown";
import "react-dropdown/style.css";

const AudioInputsDropdown: React.FC<{
  audioDevices?: Option[];
  setDeviceId: React.Dispatch<React.SetStateAction<string | null>>;
  disabled?: boolean;
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
  };

  return (
    <Dropdown
      options={ddOptions}
      onChange={handleDropdownChange}
      value={ddOptions[0]}
      disabled={props.disabled}
    />
  );
};

export default AudioInputsDropdown;
