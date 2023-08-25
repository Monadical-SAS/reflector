from pathlib import Path

import av
import numpy as np


def get_audio_waveform(path: Path | str, segments_count: int = 256) -> list[int]:
    if isinstance(path, Path):
        path = path.as_posix()

    container = av.open(path)
    stream = container.streams.get(audio=0)[0]
    duration = container.duration / av.time_base

    chunk_size_secs = duration / segments_count
    chunk_size = int(chunk_size_secs * stream.rate * stream.channels)
    if chunk_size == 0:
        # there is not enough data to fill the chunks
        # so basically we use chunk_size of 1.
        chunk_size = 1

    # 1.1 is a safety margin as it seems that pyav decode
    # does not always return the exact number of chunks
    # that we expect.
    volumes = np.zeros(int(segments_count * 1.1), dtype=int)
    current_chunk_idx = 0
    current_chunk_size = 0
    current_chunk_volume = 0

    count = 0
    frames = 0
    samples = 0
    for frame in container.decode(stream):
        data = frame.to_ndarray().flatten()
        count += len(data)
        frames += 1
        samples += frame.samples

        while len(data) > 0:
            datalen = len(data)

            # check how much we need to fill the chunk
            chunk_remaining = chunk_size - current_chunk_size
            if chunk_remaining > 0:
                volume = np.absolute(data[:chunk_remaining]).max()
                data = data[chunk_remaining:]
                current_chunk_volume = max(current_chunk_volume, volume)
                current_chunk_size += min(chunk_remaining, datalen)

            if current_chunk_size == chunk_size:
                # chunk is full, add it to the volumes
                volumes[current_chunk_idx] = current_chunk_volume
                current_chunk_idx += 1
                current_chunk_size = 0
                current_chunk_volume = 0

    volumes = volumes[:current_chunk_idx]

    # normalize the volumes 0-128
    volumes = volumes * 128 / volumes.max()

    return volumes.astype("uint8").tolist()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    parser.add_argument("--segments-count", type=int, default=256)
    args = parser.parse_args()

    print(get_audio_waveform(args.path, args.segments_count))
