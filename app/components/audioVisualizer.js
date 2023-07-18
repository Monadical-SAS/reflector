import React, { useRef, useEffect } from 'react';

function AudioVisualizer() {
    const canvasRef = useRef(null);

    useEffect(() => {
        let animationFrameId;

        const canvas = canvasRef.current;
        const context = canvas.getContext('2d');
        const analyser = new AnalyserNode(new AudioContext());

        navigator.mediaDevices.getUserMedia({ audio: true })
            .then(stream => {
                const audioContext = new (window.AudioContext || window.webkitAudioContext)();
                const source = audioContext.createMediaStreamSource(stream);
                const analyser = audioContext.createAnalyser();
                analyser.fftSize = 2048;
                source.connect(analyser);

                const bufferLength = analyser.frequencyBinCount;
                const dataArray = new Uint8Array(bufferLength);
                const barWidth = (canvas.width / bufferLength) * 2.5;
                let barHeight;
                let x = 0;

                function renderFrame() {
                    x = 0;
                    analyser.getByteFrequencyData(dataArray);
                    context.fillStyle = '#000';
                    context.fillRect(0, 0, canvas.width, canvas.height);
                    for (let i = 0; i < bufferLength; i++) {
                        barHeight = dataArray[i];

                        const red = 255;
                        const green = 250 * (i / bufferLength);
                        const blue = barHeight + (25 * (i / bufferLength));

                        context.fillStyle = `rgb(${red},${green},${blue})`;
                        context.fillRect(x, canvas.height - barHeight / 2, barWidth, barHeight / 2);

                        x += barWidth + 1;
                    }
                    animationFrameId = requestAnimationFrame(renderFrame);
                }
                renderFrame();
            });

        return () => cancelAnimationFrame(animationFrameId);
    }, []);

    return <canvas className='w-full h-16' ref={canvasRef} />;
}

export default AudioVisualizer;
