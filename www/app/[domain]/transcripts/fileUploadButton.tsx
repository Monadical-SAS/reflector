import React from "react";
import useApi from "../../lib/useApi";
import { Body_transcript_record_upload_v1_transcripts__transcript_id__record_upload_post } from "../../api";

type FileUploadButton = {
  transcriptId: string;
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
      const uploadData: Body_transcript_record_upload_v1_transcripts__transcript_id__record_upload_post =
        {
          file: file,
          // Add other properties if required by the type definition
        };

      api?.v1TranscriptRecordUpload(props.transcriptId, uploadData);
    }
  };

  return (
    <>
      <button
        className="bg-blue-400 hover:bg-blue-500 focus-visible:bg-blue-500 text-white ml-2 md:ml:4 md:h-[78px] md:min-w-[100px] text-lg"
        onClick={triggerFileUpload}
      >
        Upload File
      </button>

      <input
        type="file"
        ref={fileInputRef}
        style={{ display: "none" }}
        onChange={handleFileUpload}
      />
    </>
  );
}
