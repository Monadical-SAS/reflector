export default function Record(props) {
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
    <div className="flex flex-col justify-center h-screen">
      <div className="text-center py-6 mt-10">
        <h1 className="text-5xl font-bold text-blue-500">Reflector</h1>
        <p className="text-gray-500">Capture The Signal, Not The Noise</p>
      </div>

      <div className="flex flex-col items-center justify-center flex-grow -mt-10">
        {!props.isRecording ? (
          <button onClick={startRecording} data-color="blue">
            Record
          </button>
        ) : (
          <button onClick={stopRecording} data-color="red">
            Stop
          </button>
        )}
      </div>
    </div>
  );
}
