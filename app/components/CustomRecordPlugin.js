// Override the startRecording method so we can pass the desired stream
// Checkout: https://github.com/katspaugh/wavesurfer.js/blob/fa2bcfe/src/plugins/record.ts

import RecordPlugin from "wavesurfer.js/dist/plugins/record"

const MIME_TYPES = ['audio/webm', 'audio/wav', 'audio/mpeg', 'audio/mp4', 'audio/mp3']
const findSupportedMimeType = () => MIME_TYPES.find((mimeType) => MediaRecorder.isTypeSupported(mimeType))

class CustomRecordPlugin extends RecordPlugin {
  static create(options) {
    return new CustomRecordPlugin(options || {})
  }
  startRecording(stream) {
    this.preventInteraction()
    this.cleanUp()

    const onStop = this.render(stream)
    const mediaRecorder = new MediaRecorder(stream, {
      mimeType: this.options.mimeType || findSupportedMimeType(),
      audioBitsPerSecond: this.options.audioBitsPerSecond,
    })
    const recordedChunks = []

    mediaRecorder.addEventListener('dataavailable', (event) => {
      if (event.data.size > 0) {
        recordedChunks.push(event.data)
      }
    })

    mediaRecorder.addEventListener('stop', () => {
      onStop()
      this.loadBlob(recordedChunks, mediaRecorder.mimeType)
      this.emit('stopRecording')
    })

    mediaRecorder.start()

    this.emit('startRecording')

    this.mediaRecorder = mediaRecorder
  }
}

export default CustomRecordPlugin;