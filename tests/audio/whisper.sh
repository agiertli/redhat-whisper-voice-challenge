#!/bin/bash

# Default values
MODE="transcriptions"
LANGUAGE="en"
TO_LANGUAGE=""
BASE_URL="${WHISPER_BASE_URL:-https://your-model-route.apps.your-cluster.example.com/v1/audio}"
MODEL="${WHISPER_MODEL:-whisper2}"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -t|--translate)
            MODE="translations"
            shift
            ;;
        -l|--language)
            [[ $# -ge 2 ]] || { echo "Missing language code" >&2; exit 1; }
            LANGUAGE="$2"
            shift 2
            ;;
        -T|--to-language)
            [[ $# -ge 2 ]] || { echo "Missing target language code" >&2; exit 1; }
            TO_LANGUAGE="$2"
            shift 2
            ;;
        -*)
            echo "Unknown option: $1"
            echo "Usage: $0 [-t|--translate] [-l|--language <code>] [-T|--to-language <code>] <audio-file>"
            echo "  -t, --translate      Enable translation mode"
            echo "  -l, --language       Source language code (default: en)"
            echo "  -T, --to-language    Target language for translation (only with -t)"
            echo ""
            echo "Examples:"
            echo "  $0 audio.wav                    # Transcribe English audio to English text"
            echo "  $0 -l cs audio.wav              # Transcribe Czech audio to Czech text"
            echo "  $0 -t -l cs audio.wav           # Translate Czech audio to English text"
            echo "  $0 -t -l en -T cs audio.wav     # Translate English audio to Czech text"
            exit 1
            ;;
        *)
            AUDIO_FILE="$1"
            shift
            ;;
    esac
done

if [ -z "$AUDIO_FILE" ]; then
    echo "Usage: $0 [-t|--translate] [-l|--language <code>] [-T|--to-language <code>] <audio-file>"
    echo "  -t, --translate      Enable translation mode"
    echo "  -l, --language       Source language code (default: en)"
    echo "  -T, --to-language    Target language for translation (only with -t)"
    echo ""
    echo "Examples:"
    echo "  $0 audio.wav                    # Transcribe English audio to English text"
    echo "  $0 -l cs audio.wav              # Transcribe Czech audio to Czech text"
    echo "  $0 -t -l cs audio.wav           # Translate Czech audio to English text"
    echo "  $0 -t -l en -T cs audio.wav     # Translate English audio to Czech text"
    exit 1
fi

if [ ! -f "$AUDIO_FILE" ]; then
    echo "Error: File '$AUDIO_FILE' not found"
    exit 1
fi

# Use an argument array: filenames and values are data, never shell code.
# Set CURL_CA_BUNDLE for a private CA rather than bypassing TLS verification.
CURL_ARGS=(--fail --show-error -X POST "${BASE_URL}/${MODE}"
    -F "file=@${AUDIO_FILE}" --form-string "model=${MODEL}"
    --form-string "response_format=json" --form-string "language=${LANGUAGE}")
if [[ "$MODE" == translations && -n "$TO_LANGUAGE" ]]; then
    CURL_ARGS+=(--form-string "to_language=${TO_LANGUAGE}")
fi
curl "${CURL_ARGS[@]}"
