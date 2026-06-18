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
            LANGUAGE="$2"
            shift 2
            ;;
        -T|--to-language)
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

# Build curl command
CURL_CMD="curl -X POST \"${BASE_URL}/${MODE}\" \
    -H \"Content-Type: multipart/form-data\" \
    -F \"file=@${AUDIO_FILE}\" \
    -F \"model=${MODEL}\" \
    -F \"response_format=json\" \
    -k"

# Add language parameters based on mode
if [ "$MODE" = "transcriptions" ]; then
    # Transcription: only source language matters
    CURL_CMD="${CURL_CMD} -F \"language=${LANGUAGE}\""
elif [ "$MODE" = "translations" ]; then
    # Translation: source language and optionally target language
    CURL_CMD="${CURL_CMD} -F \"language=${LANGUAGE}\""
    if [ -n "$TO_LANGUAGE" ]; then
        CURL_CMD="${CURL_CMD} -F \"to_language=${TO_LANGUAGE}\""
    fi
fi

eval $CURL_CMD
