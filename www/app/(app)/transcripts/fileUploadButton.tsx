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
      const maxChunkSize = 50 * 1024 * 1024; // 50 MB
      const totalChunks = Math.ceil(file.size / maxChunkSize);
      let chunkNumber = 0;
      let start = 0;
      let uploadedSize = 0;

      api?.httpRequest.config.interceptors.request.use((request) => {
        request.onUploadProgress = (progressEvent) => {
          const currentProgress = Math.floor(
            ((uploadedSize + progressEvent.loaded) / file.size) * 100,
          );
          setProgress(currentProgress);
        };
        return request;
      });

      const uploadNextChunk = async () => {
        if (chunkNumber == totalChunks) return;

        const chunkSize = Math.min(maxChunkSize, file.size - start);
        const end = start + chunkSize;
        const chunk = file.slice(start, end);

        await api?.v1TranscriptRecordUpload({
          transcriptId: props.transcriptId,
          formData: {
            chunk,
          },
          chunkNumber,
          totalChunks,
        });

        uploadedSize += chunkSize;
        chunkNumber++;
        start = end;

        uploadNextChunk();
      };

      uploadNextChunk();
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
