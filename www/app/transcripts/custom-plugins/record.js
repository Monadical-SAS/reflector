// Override the startRecording method so we can pass the desired stream
// Checkout: https://github.com/katspaugh/wavesurfer.js/blob/fa2bcfe/src/plugins/record.ts

import RecordPlugin from "wavesurfer.js/dist/plugins/record";

const MIME_TYPES = [
  "audio/webm",
  "audio/wav",
  "audio/mpeg",
  "audio/mp4",
  "audio/mp3",
];
const findSupportedMimeType = () =>
  MIME_TYPES.find((mimeType) => MediaRecorder.isTypeSupported(mimeType));

class CustomRecordPlugin extends RecordPlugin {
  static create(options) {
    return new CustomRecordPlugin(options || {});
  }
  render(stream) {
    if (!this.wavesurfer) return () => undefined;

    const container = this.wavesurfer.getWrapper();
    const canvas = document.createElement("canvas");
    canvas.width = container.clientWidth;
    canvas.height = container.clientHeight;
    canvas.style.zIndex = "10";
    container.appendChild(canvas);

    const canvasCtx = canvas.getContext("2d");
    const audioContext = new AudioContext();
    const source = audioContext.createMediaStreamSource(stream);
    const analyser = audioContext.createAnalyser();
    analyser.fftSize = 2 ** 5;
    source.connect(analyser);
    const bufferLength = analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);

    let animationId, previousTimeStamp;
    const DATA_SIZE = 128.0;
    const BUFFER_SIZE = 2 ** 8;
    const dataBuffer = new Array(BUFFER_SIZE).fill(DATA_SIZE);

    const drawWaveform = (timeStamp) => {
      if (!canvasCtx) return;

      analyser.getByteTimeDomainData(dataArray);
      canvasCtx.clearRect(0, 0, canvas.width, canvas.height);
      canvasCtx.fillStyle = "#cc3347";

      if (previousTimeStamp === undefined) {
        previousTimeStamp = timeStamp;
        dataBuffer.push(Math.min(...dataArray));
        dataBuffer.splice(0, 1);
      }
      const elapsed = timeStamp - previousTimeStamp;
      if (elapsed > 10) {
        previousTimeStamp = timeStamp;
        dataBuffer.push(Math.min(...dataArray));
        dataBuffer.splice(0, 1);
      }

      // Drawing
      const sliceWidth = canvas.width / dataBuffer.length;
      let x = 0;

      for (let i = 0; i < dataBuffer.length; i++) {
        const y = (canvas.height * dataBuffer[i]) / (2 * DATA_SIZE);
        const sliceHeight =
          ((1 - canvas.height) * dataBuffer[i]) / DATA_SIZE + canvas.height;

        canvasCtx.fillRect(x, y, (sliceWidth * 2) / 3, sliceHeight);
        x += sliceWidth;
      }

      animationId = requestAnimationFrame(drawWaveform);
    };

    drawWaveform();

    return () => {
      if (animationId) {
        cancelAnimationFrame(animationId);
      }

      if (source) {
        source.disconnect();
        source.mediaStream.getTracks().forEach((track) => track.stop());
      }

      if (audioContext) {
        audioContext.close();
      }

      canvas?.remove();
    };
  }
  startRecording(stream) {
    this.preventInteraction();
    this.cleanUp();

    const onStop = this.render(stream);
    const mediaRecorder = new MediaRecorder(stream, {
      mimeType: this.options.mimeType || findSupportedMimeType(),
      audioBitsPerSecond: this.options.audioBitsPerSecond,
    });
    const recordedChunks = [];

    mediaRecorder.addEventListener("dataavailable", (event) => {
      if (event.data.size > 0) {
        recordedChunks.push(event.data);
      }
    });

    mediaRecorder.addEventListener("stop", () => {
      onStop();
      this.loadBlob(recordedChunks, mediaRecorder.mimeType);
      this.emit("stopRecording");
    });

    mediaRecorder.start();

    this.emit("startRecording");

    this.mediaRecorder = mediaRecorder;
  }
}

export default CustomRecordPlugin;
