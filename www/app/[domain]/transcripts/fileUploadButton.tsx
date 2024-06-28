import React from "react";
import useApi from "../../lib/useApi";
import { Button } from "@chakra-ui/react";

type FileUploadButton = {
  transcriptId: string;
  disabled?: boolean;
};

export default function FileUploadButton(props: FileUploadButton) {
  const fileInputRef = React.useRef<HTMLInputElement>(null);
  const api = useApi();

  const triggerFileUpload = () => {
    fileInputRef.current?.click();
  };

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];

    if (file) {
      console.log("Calling api.v1TranscriptRecordUpload()...");

      // Create an object of the expected type
      const uploadData = {
        file: file,
        // Add other properties if required by the type definition
      };

      api?.v1TranscriptRecordUpload(props.transcriptId, uploadData);
    }
  };

  return (
    <>
      <Button
        onClick={triggerFileUpload}
        colorScheme="blue"
        mr={2}
        isDisabled={props.disabled}
      >
        Upload File
      </Button>

      <input
        type="file"
        ref={fileInputRef}
        style={{ display: "none" }}
        onChange={handleFileUpload}
      />
    </>
  );
}
