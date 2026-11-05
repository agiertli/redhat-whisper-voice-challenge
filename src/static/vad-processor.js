class VADProcessor extends AudioWorkletProcessor {
    constructor() {
        super();
        this.buffers = [];
        this.recording = true;

        this.port.onmessage = (e) => {
            if (e.data.type === 'stop') {
                this.recording = false;
            } else if (e.data.type === 'getChunk') {
                const merged = this._mergeBuffers(this.buffers);
                this.buffers = [];
                this.port.postMessage({ type: 'chunk', samples: merged }, [merged.buffer]);
            } else if (e.data.type === 'clearBuffers') {
                this.buffers = [];
            }
        };
    }

    process(inputs) {
        if (!this.recording) return false;
        const input = inputs[0];
        if (!input || !input[0] || input[0].length === 0) return true;

        const channelData = input[0];
        const buffer = new Float32Array(channelData);

        let sum = 0;
        for (let i = 0; i < buffer.length; i++) {
            sum += buffer[i] * buffer[i];
        }
        const rms = Math.sqrt(sum / buffer.length);

        this.buffers.push(buffer);
        this.port.postMessage({ type: 'rms', rms });

        return true;
    }

    _mergeBuffers(buffers) {
        const length = buffers.reduce((acc, buf) => acc + buf.length, 0);
        const merged = new Float32Array(length);
        let offset = 0;
        for (const buf of buffers) {
            merged.set(buf, offset);
            offset += buf.length;
        }
        return merged;
    }
}

registerProcessor('vad-processor', VADProcessor);
