import React, { useState } from "react";
import useApi from "../../lib/useApi";
import { Button, CircularProgress } from "@chakra-ui/react";

type FileUploadButton = {
  transcriptId: string;
};

export default function FileUploadButton(props: FileUploadButton) {
  const fileInputRef = React.useRef<HTMLInputElement>(null);
  const api = useApi();
  const [progress, setProgress] = useState(0);
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

      api?.httpRequest.config.interceptors.request.use((request) => {
        request.onUploadProgress = (progressEvent) => {
          setProgress((progressEvent.progress || 0) * 100);
        };
        return request;
      });
      api?.v1TranscriptRecordUpload({
        transcriptId: props.transcriptId,
        formData: uploadData,
      });
    }
  };

  return (
    <>
      <Button
        onClick={triggerFileUpload}
        colorScheme="blue"
        mr={2}
        isDisabled={progress > 0}
      >
        {progress > 0 && progress < 100 ? (
          <>
            Uploading...&nbsp;
            <CircularProgress size="20px" value={progress} />
          </>
        ) : (
          <>Select File</>
        )}
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
