chrome.runtime.onMessage.addListener(({ message }) => {
    if (message == 'start') startRecording()
})

const startRecording = () => {
    // chrome.storage.local.set({ transcript: '' })

    const DISPLAY_MEDIA_CONSTRAINS = {
        video: true, // Required for getMediaDisplay to work. We don't use video
        audio: {
            noiseSuppression: false,
            echoCancellation: false,
        },
        selfBrowserSurface: "include",
    }

    navigator.mediaDevices.getDisplayMedia(DISPLAY_MEDIA_CONSTRAINS).then(async screenStream => {
        // if(!apiKey) return alert('You must provide a Deepgram API Key in the options page.')

        if (screenStream.getAudioTracks().length == 0) return alert('You must share your tab with audio. Refresh the page.')
        screenStream.getVideoTracks().forEach(track => screenStream.removeTrack(track))

        const micStream = await navigator.mediaDevices.getUserMedia({ audio: true })
        const audioContext = new AudioContext()
        const streams = [screenStream, micStream]
        const mixed = mix(audioContext, streams)
        const mediaRecorder = new MediaRecorder(mixed, { mimeType: 'audio/webm' })

        // socket = new WebSocket('wss://api.deepgram.com/v1/listen?model=general-enhanced', ['token', apiKey])

        const recordedChunks = []
        mediaRecorder.addEventListener('dataavailable', evt => {
            // if(evt.data.size > 0 && socket.readyState == 1) socket.send(evt.data)
            if (evt.data.size > 0) recordedChunks.push(evt.data)
        })
        mediaRecorder.addEventListener("start", () => {
            // ...
        });
        mediaRecorder.addEventListener("stop", () => {
            streams.forEach(stream => stream.getTracks().forEach(track => track.stop()))
            // if(socket.readyState == 1) socket.close()

            // Only used for testing
            downloadRecording(recordedChunks)
        });

        // socket.onopen = () => { mediaRecorder.start(250) }

        // socket.onmessage = msg => {
        //     const { transcript } = JSON.parse(msg.data).channel.alternatives[0]
        //     if(transcript) {
        //         chrome.storage.local.get('transcript', data => {
        //             chrome.storage.local.set({ transcript: data.transcript += ' ' + transcript })

        //             // Throws error when popup is closed, so this swallows the errors.
        //             chrome.runtime.sendMessage({ message: 'transcriptavailable' }).catch(err => ({}))
        //         })
        //     }
        // }

        mediaRecorder.start()

        chrome.runtime.onMessage.addListener(({ message }) => {
            if (message == 'stop') {
                // socket.close()
                console.log('Transcription ended')
                mediaRecorder?.stop()
            }
        })
    })
}

const downloadRecording = (recordedChunks) => {
    const blob = new Blob(recordedChunks, {
        type: 'audio/webm'
    });
    const url = URL.createObjectURL(blob);

    const link = document.createElement("a")
    link.setAttribute("href", url);
    link.setAttribute("download", "reflector-recording.webm");
    link.style.display = "none";

    document.body.appendChild(link);
    link.click();

    window.URL.revokeObjectURL(url);
    link.remove();
}

// https://stackoverflow.com/a/47071576
function mix(audioContext, streams) {
    const dest = audioContext.createMediaStreamDestination()
    streams.forEach(stream => {
        const source = audioContext.createMediaStreamSource(stream)
        source.connect(dest);
    })
    return dest.stream
}

console.log("Reflector extension: content script loaded")
