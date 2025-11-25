import React, { useState } from "react";
import { useTranscriptUploadAudio } from "../../lib/apiHooks";
import { Button, Spinner } from "@chakra-ui/react";
import { useError } from "../../(errors)/errorContext";

type FileUploadButton = {
  transcriptId: string;
  onUploadComplete?: () => void;
};

export default function FileUploadButton(props: FileUploadButton) {
  const fileInputRef = React.useRef<HTMLInputElement>(null);
  const uploadMutation = useTranscriptUploadAudio();
  const { setError } = useError();
  const [progress, setProgress] = useState(0);
  const triggerFileUpload = () => {
    fileInputRef.current?.click();
  };

  const handleFileUpload = async (
    event: React.ChangeEvent<HTMLInputElement>,
  ) => {
    const file = event.target.files?.[0];

    if (file) {
      const maxChunkSize = 50 * 1024 * 1024; // 50 MB
      const totalChunks = Math.ceil(file.size / maxChunkSize);
      let chunkNumber = 0;
      let start = 0;
      let uploadedSize = 0;

      const uploadNextChunk = async () => {
        if (chunkNumber == totalChunks) {
          setProgress(0);
          props.onUploadComplete?.();
          return;
        }

        const chunkSize = Math.min(maxChunkSize, file.size - start);
        const end = start + chunkSize;
        const chunk = file.slice(start, end);

        try {
          const formData = new FormData();
          formData.append("chunk", chunk);

          await uploadMutation.mutateAsync({
            params: {
              path: {
                transcript_id: props.transcriptId,
              },
              query: {
                chunk_number: chunkNumber,
                total_chunks: totalChunks,
              },
            },
            body: formData as any,
          });

          uploadedSize += chunkSize;
          const currentProgress = Math.floor((uploadedSize / file.size) * 100);
          setProgress(currentProgress);

          chunkNumber++;
          start = end;

          await uploadNextChunk();
        } catch (error) {
          setError(error as Error, "Failed to upload file");
          setProgress(0);
        }
      };

      uploadNextChunk();
    }
  };

  return (
    <>
      <Button onClick={triggerFileUpload} mr={2} disabled={progress > 0}>
        {progress > 0 && progress < 100 ? (
          <>
            Uploading...&nbsp;
            <Spinner size="sm" />
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
