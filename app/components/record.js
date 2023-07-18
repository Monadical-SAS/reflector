import AudioVisualizer from "./audioVisualizer.js";

export default function Recorder(props) {
  let mediaRecorder = null; // mediaRecorder instance

  const startRecording = () => {
    navigator.mediaDevices.getUserMedia({ audio: true }).then((stream) => {
      mediaRecorder = new MediaRecorder(stream);
      mediaRecorder.start();
      props.onRecord(true);
    });
  };

  const stopRecording = () => {
    if (mediaRecorder) {
      mediaRecorder.stop();
      props.onRecord(false);
    }
  };

  return (
      <div className="flex flex-col items-center justify-center">
        {props.isRecording && <AudioVisualizer />}

        {props.isRecording ? (
          <button onClick={stopRecording} data-color="red">
            Stop
          </button>
        ) : (
          <button onClick={startRecording} data-color="blue">
            Record
          </button>
        )}
      </div>
  );
}
