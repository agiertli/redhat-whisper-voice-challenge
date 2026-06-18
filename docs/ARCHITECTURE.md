# Architecture

The Red Hat Whisper Voice Challenge is a Flask web application that captures audio in the browser, sends it to a Whisper speech-to-text model running on OpenShift AI via vLLM, and displays real-time metrics from Prometheus and NVIDIA DCGM.

## System Architecture Diagram

```mermaid
flowchart TB
    subgraph Browser["🌐 Browser (User)"]
        MicSelect["🎙️ Microphone Selection<br/>(Dropdown)"]
        WebAudio["🎵 Web Audio API<br/>ScriptProcessorNode<br/>Raw Audio Samples"]
        WAVEncoder["📦 Client-side WAV Encoder<br/>• Resample to 16kHz<br/>• Convert to Mono<br/>• 16-bit PCM<br/>• RIFF/WAVE Format"]
        
        MicSelect --> WebAudio
        WebAudio --> WAVEncoder
    end
    
    subgraph OpenShift["☁️ OpenShift / Kubernetes"]
        subgraph WhisperUI["Whisper UI Service"]
            Route["🌍 Route (TLS Edge)"]
            Service["⚙️ Service (ClusterIP)<br/>Port: 8080"]
            Deployment["📦 Deployment<br/>UBI9 Python 3.11 + Flask<br/>Gunicorn"]
            ConfigMap["📝 ConfigMap<br/>• WHISPER_API_URL<br/>• SUPPORTED_LANGUAGES<br/>• CONFERENCE_NAME"]
            
            Route --> Service
            Service --> Deployment
            Deployment -.reads.-> ConfigMap
        end
        
        subgraph WhisperAPI["Whisper API (vLLM)"]
            VLLM["🤖 OpenShift AI 3.3<br/>whisper-large-v3-turbo (809M params)<br/>/v1/audio/transcriptions<br/>Input: WAV (16kHz, mono)<br/>Output: JSON or SSE stream"]
        end
        
        Deployment -->|"HTTP POST<br/>WAV file"| VLLM
    end
    
    WAVEncoder -->|"HTTP POST /transcribe<br/>WAV file (16kHz, mono, 16-bit)"| Route
    VLLM -->|"JSON Response<br/>{text, usage}"| Deployment
    Deployment -->|"JSON"| Browser
    
    style Browser fill:#e1f5ff
    style OpenShift fill:#fff4e1
    style WhisperUI fill:#e8f5e9
    style WhisperAPI fill:#fce4ec
    style WAVEncoder fill:#90caf9
    style VLLM fill:#f48fb1
```

## Data Flow

```mermaid
sequenceDiagram
    participant User
    participant Browser
    participant WebAudio as Web Audio API
    participant Flask as Flask Backend
    participant Whisper as Whisper API (vLLM)
    
    User->>Browser: 1. Select microphone
    User->>Browser: 2. Click "Start Recording"
    Browser->>WebAudio: 3. Request microphone access
    WebAudio-->>Browser: 4. Grant access
    activate WebAudio
    Note over WebAudio: Capturing raw audio samples<br/>via ScriptProcessorNode
    User->>Browser: 5. Speak into microphone
    User->>Browser: 6. Click "Stop Recording"
    deactivate WebAudio
    Browser->>Browser: 7. Convert samples to WAV<br/>(16kHz, mono, 16-bit PCM)
    Browser->>Flask: 8. POST /transcribe<br/>(WAV file + language)
    Flask->>Flask: 9. Save WAV to /tmp
    Flask->>Whisper: 10. POST /v1/audio/transcriptions<br/>(WAV file)
    activate Whisper
    Note over Whisper: Processing audio with<br/>whisper-large-v3-FP8-dynamic
    Whisper-->>Flask: 11. JSON {text, usage}
    deactivate Whisper
    Flask->>Flask: 12. Cleanup temp files
    Flask-->>Browser: 13. JSON response
    Browser->>User: 14. Display transcription
```

## Component Details

```mermaid
graph LR
    subgraph Frontend["Frontend Components"]
        HTML[HTML/CSS/JS]
        WebAudioAPI[Web Audio API]
        WAVLib[WAV Encoder Library]
    end
    
    subgraph Backend["Backend Components"]
        Flask[Flask Framework]
        Gunicorn[Gunicorn WSGI]
        Requests[Requests Library]
    end
    
    subgraph Infrastructure["Infrastructure"]
        Route[OpenShift Route<br/>TLS Edge]
        Service[Kubernetes Service]
        ConfigMap[ConfigMap]
        Deployment[Deployment]
    end
    
    subgraph AI["AI/ML"]
        WhisperModel[Whisper Large v3<br/>FP8 Quantized]
        vLLM[vLLM Runtime]
    end
    
    HTML --> WebAudioAPI
    WebAudioAPI --> WAVLib
    WAVLib --> Route
    Route --> Service
    Service --> Deployment
    Deployment --> Flask
    Flask --> Gunicorn
    Flask --> Requests
    ConfigMap --> Deployment
    Requests --> vLLM
    vLLM --> WhisperModel
    
    style Frontend fill:#e3f2fd
    style Backend fill:#f3e5f5
    style Infrastructure fill:#e8f5e9
    style AI fill:#fff3e0
```

## Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | Web Audio API | Audio capture & processing |
| | JavaScript | WAV encoding & UI logic |
| | HTML/CSS | User interface |
| **Backend** | Flask 3.0.3 | Web framework |
| | Gunicorn 22.0.0 | WSGI server |
| | Python 3.11 | Runtime |
| **Container** | UBI9 Python 3.11 | Base image |
| | Podman/Docker | Build tool |
| **Platform** | OpenShift 4.x | Kubernetes platform |
| | Helm 3.x | Package manager |
| **AI/ML** | Whisper Large v3 Turbo | Speech-to-text model (809M params) |
| | vLLM 0.13 | Model serving runtime with SSE streaming |
| | OpenShift AI 3.3 | ML platform |

## Audio Processing Pipeline

```mermaid
flowchart LR
    A[Microphone] --> B[Web Audio API<br/>48kHz Stereo]
    B --> C[ScriptProcessorNode<br/>4096 samples/buffer]
    C --> D[Float32Array Buffers]
    D --> E[Resample to 16kHz]
    E --> F[Convert to Mono]
    F --> G[Convert to 16-bit PCM]
    G --> H[Add WAV Header<br/>RIFF/WAVE]
    H --> I[WAV Blob]
    I --> J[HTTP POST to Flask]
    J --> K[Whisper API]
    K --> L[Transcription JSON]
    
    style A fill:#4caf50
    style I fill:#2196f3
    style K fill:#ff9800
    style L fill:#9c27b0
```

## Challenge Scoring (Game Mode)

The root route (`/`) serves an interactive voice challenge with accuracy scoring.

### Scoring Algorithm

**Levenshtein Distance-based Similarity:**

1. **Text Normalization** (before comparison):
   ```javascript
   - Convert to lowercase
   - Trim whitespace
   - Remove punctuation: .,!?;:
   - Normalize multiple spaces to single space
   ```

2. **Edit Distance Calculation:**
   - Character-by-character comparison
   - Counts minimum edits needed (insertions, deletions, substitutions)
   - Classic dynamic programming algorithm

3. **Similarity Score Formula:**
   ```
   similarity = (longer.length - editDistance) / longer.length
   accuracy = similarity × 100
   ```

4. **Visual Feedback:**
   - **≥90%** = Green (Success) + Prize notification
   - **70-89%** = Blue (Good)
   - **<70%** = Orange (Needs improvement)

### Example Scoring

| Expected | Transcribed | Edit Distance | Accuracy |
|----------|-------------|---------------|----------|
| "openshift je skvelý produkt" | "openshift je skvely produkt" | 1 | 96.7% |
| "red hat ai" | "redhat ai" | 1 | 90.0% |
| "artificial intelligence" | "artifical inteligence" | 3 | 87.0% |

### Limitations

- **Word order sensitive**: "Red Hat AI" vs "AI Red Hat" = lower score
- **No semantic understanding**: "vehicle" vs "car" treated as completely different
- **Space-sensitive**: Missing/extra spaces affect score
- **Character-level**: Works well for typos, not for paraphrasing

### Implementation Location

- **File**: `src/templates/index.html`
- **Functions**: `levenshteinDistance()`, `levenshteinSimilarity()`
- **Execution**: Client-side JavaScript (no backend processing)

## Deployment Architecture

```mermaid
graph TB
    subgraph Internet
        User((User Browser))
    end
    
    subgraph OpenShift["OpenShift Cluster"]
        subgraph Namespace["Namespace: whisper"]
            Route[Route<br/>TLS Termination]
            
            subgraph WhisperUIService["Whisper UI"]
                Service1[Service<br/>ClusterIP:8080]
                Pod1[Pod: whisper-ui<br/>Flask + Gunicorn]
                CM1[ConfigMap<br/>whisper-ui-config]
                
                Service1 --> Pod1
                Pod1 -.reads.-> CM1
            end
            
            subgraph WhisperAPIService["Whisper API"]
                Service2[Service<br/>whisper2]
                Pod2[Pod: vLLM<br/>Whisper Model]
                
                Service2 --> Pod2
            end
            
            Route --> Service1
            Pod1 -->|HTTP POST| Service2
        end
    end
    
    User -->|HTTPS| Route
    
    style User fill:#4caf50
    style Route fill:#2196f3
    style Service1 fill:#ff9800
    style Service2 fill:#ff9800
    style Pod1 fill:#9c27b0
    style Pod2 fill:#9c27b0
```
