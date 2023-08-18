// Source code: https://github.com/katspaugh/wavesurfer.js/blob/fa2bcfe/src/plugins/record.ts
/**
 * Record audio from the microphone, render a waveform and download the audio.
 */

import BasePlugin, {
  type BasePluginEvents,
} from "wavesurfer.js/dist/base-plugin";

export type RecordPluginOptions = {
  mimeType?: MediaRecorderOptions["mimeType"];
  audioBitsPerSecond?: MediaRecorderOptions["audioBitsPerSecond"];
};

export type RecordPluginEvents = BasePluginEvents & {
  startRecording: [];
  stopRecording: [];
};

const MIME_TYPES = [
  "audio/webm",
  "audio/wav",
  "audio/mpeg",
  "audio/mp4",
  "audio/mp3",
];
const findSupportedMimeType = () =>
  MIME_TYPES.find((mimeType) => MediaRecorder.isTypeSupported(mimeType));

class RecordPlugin extends BasePlugin<RecordPluginEvents, RecordPluginOptions> {
  private mediaRecorder: MediaRecorder | null = null;
  private recordedUrl = "";
  private savedCursorWidth = 1;
  private savedInteractive = true;

  public static create(options?: RecordPluginOptions) {
    return new RecordPlugin(options || {});
  }

  private preventInteraction() {
    if (this.wavesurfer) {
      this.savedCursorWidth = this.wavesurfer.options.cursorWidth || 1;
      this.savedInteractive = this.wavesurfer.options.interact || true;
      this.wavesurfer.options.cursorWidth = 0;
      this.wavesurfer.options.interact = false;
    }
  }

  private restoreInteraction() {
    if (this.wavesurfer) {
      this.wavesurfer.options.cursorWidth = this.savedCursorWidth;
      this.wavesurfer.options.interact = this.savedInteractive;
    }
  }

  onInit() {
    this.preventInteraction();
  }

  private loadBlob(data: Blob[], type: string) {
    const blob = new Blob(data, { type });
    this.recordedUrl = URL.createObjectURL(blob);
    this.restoreInteraction();
    this.wavesurfer?.load(this.recordedUrl);
  }

  render(stream: MediaStream): () => void {
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

    let animationId: number, previousTimeStamp: number;
    const DATA_SIZE = 128.0;
    const BUFFER_SIZE = 2 ** 8;
    const dataBuffer = new Array(BUFFER_SIZE).fill(DATA_SIZE);

    const drawWaveform = (timeStamp: number) => {
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

    drawWaveform(0);

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

  private cleanUp() {
    this.stopRecording();
    this.wavesurfer?.empty();
    if (this.recordedUrl) {
      URL.revokeObjectURL(this.recordedUrl);
      this.recordedUrl = "";
    }
  }

  public async startRecording(stream: MediaStream) {
    this.preventInteraction();
    this.cleanUp();

    const onStop = this.render(stream);
    const mediaRecorder = new MediaRecorder(stream, {
      mimeType: this.options.mimeType || findSupportedMimeType(),
      audioBitsPerSecond: this.options.audioBitsPerSecond,
    });
    const recordedChunks: Blob[] = [];

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

  public isRecording(): boolean {
    return this.mediaRecorder?.state === "recording";
  }

  public stopRecording() {
    if (this.isRecording()) {
      this.mediaRecorder?.stop();
    }
  }

  public getRecordedUrl(): string {
    return this.recordedUrl;
  }

  public destroy() {
    super.destroy();
    this.cleanUp();
  }
}

export default RecordPlugin;
