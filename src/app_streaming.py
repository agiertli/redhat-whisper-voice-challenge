from flask import Flask, render_template, request, jsonify, Response, stream_with_context
import requests
import os
import tempfile
import json
import logging
import sys
import time
from datetime import datetime
from kubernetes import client, config
import urllib3

# Disable SSL warnings for internal cluster communication
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

WHISPER_API_URL = os.getenv('WHISPER_API_URL', 'http://whisper-model.whisper.svc.cluster.local:8080/v1/audio/transcriptions')
WHISPER_MODEL_NAME = os.getenv('WHISPER_MODEL_NAME', 'whisper-turbo')
MODEL_DISPLAY_NAME = os.getenv('MODEL_DISPLAY_NAME', 'Whisper Turbo')
CONFERENCE_NAME = os.getenv('CONFERENCE_NAME', 'Red Hat Whisper Voice Challenge')
SUPPORTED_LANGUAGES = json.loads(os.getenv('SUPPORTED_LANGUAGES',
    '{"sk": "Slovenčina", "cs": "Čeština", "hu": "Magyar", "de": "Deutsch", "es": "Español", "fr": "Français", "en": "English"}'))
DCGM_EXPORTER_URL = os.getenv('DCGM_EXPORTER_URL', 'http://nvidia-dcgm-exporter.nvidia-gpu-operator.svc:9400/metrics')
WHISPER_NAMESPACE = os.getenv('WHISPER_NAMESPACE', 'whisper')
THANOS_QUERIER_URL = os.getenv('THANOS_QUERIER_URL', 'https://thanos-querier.openshift-monitoring.svc.cluster.local:9091')

from urllib.parse import urlparse
_parsed_url = urlparse(WHISPER_API_URL)
VLLM_METRICS_URL = f"{_parsed_url.scheme}://{_parsed_url.netloc}/metrics"

# Voice Challenge Game Settings
REQUIRED_CHALLENGE_LANGUAGE = os.getenv('REQUIRED_CHALLENGE_LANGUAGE', 'sk')
CHALLENGE_COUNT = int(os.getenv('CHALLENGE_COUNT', '5'))
WIN_THRESHOLD = int(os.getenv('WIN_THRESHOLD', '4'))


CHALLENGES_FILE = os.getenv('CHALLENGES_FILE', os.path.join(os.path.dirname(__file__), '..', 'challenges.json'))
try:
    with open(CHALLENGES_FILE, 'r', encoding='utf-8') as f:
        CHALLENGE_PHRASES = json.load(f)
except FileNotFoundError:
    CHALLENGE_PHRASES = {"en": ["Artificial intelligence transforms business", "Kubernetes simplifies application deployment", "Cloud solutions increase efficiency"]}
    logger.warning(f"Challenges file not found at {CHALLENGES_FILE}, using defaults")

logger.info(f"Whisper UI starting - API URL: {WHISPER_API_URL}")
logger.info(f"Model name: {WHISPER_MODEL_NAME}")
logger.info(f"Supported languages: {list(SUPPORTED_LANGUAGES.keys())}")
logger.info(f"Challenge languages loaded: {list(CHALLENGE_PHRASES.keys())}")
logger.info(f"DCGM Exporter URL: {DCGM_EXPORTER_URL}")
logger.info(f"Thanos Querier URL: {THANOS_QUERIER_URL}")

# Global metrics tracking
last_chunk_metrics = {
    'tokens': 0,
    'duration_ms': 0,
    'timestamp': time.time()
}

# GPU utilization history - sliding window for histogram
# Stores samples over last 60 seconds to visualize activity patterns
from collections import deque

gpu_util_history = deque(maxlen=60)  # 60 samples = 1 minute at 1 sample/sec
last_gpu_sample_time = 0

# Last activity tracking for "seconds since" metric
last_request_time = 0

# Initialize Kubernetes client
try:
    config.load_incluster_config()  # Running inside a pod
    k8s_v1 = client.CoreV1Api()
    logger.info("Kubernetes client initialized (in-cluster config)")
except Exception as e:
    logger.warning(f"Failed to load in-cluster config: {e}. DCGM auto-discovery will not work.")
    k8s_v1 = None

# Cache for DCGM exporter URL discovery
dcgm_url_cache = {
    'url': None,
    'timestamp': 0,
    'ttl': 300  # Cache for 5 minutes
}

def query_vllm_gauge(metric_name):
    """Scrape a real-time gauge directly from the vLLM /metrics endpoint."""
    try:
        response = requests.get(VLLM_METRICS_URL, timeout=2, verify=False)
        if response.status_code != 200:
            return None
        for line in response.text.split('\n'):
            if line.startswith(metric_name + '{') or line.startswith(metric_name + ' '):
                parts = line.split()
                if len(parts) >= 2:
                    return float(parts[-1])
        return None
    except Exception as e:
        logger.error(f"vLLM gauge query error for {metric_name}: {e}")
        return None


vllm_metrics_cache = {
    'data': None,
    'timestamp': 0,
    'ttl': 30
}

def query_prometheus(promql):
    """Execute a PromQL instant query against the Thanos querier."""
    try:
        token_path = '/var/run/secrets/kubernetes.io/serviceaccount/token'
        with open(token_path, 'r') as f:
            token = f.read().strip()

        response = requests.get(
            f"{THANOS_QUERIER_URL}/api/v1/query",
            params={'query': promql},
            headers={'Authorization': f'Bearer {token}'},
            timeout=5,
            verify=False
        )

        if response.status_code != 200:
            logger.warning(f"Prometheus query failed ({response.status_code}): {promql}")
            return None

        data = response.json()
        if data.get('status') != 'success':
            logger.warning(f"Prometheus query error: {data.get('error', 'unknown')}")
            return None

        result = data.get('data', {}).get('result', [])
        if not result:
            return 0.0

        return float(result[0]['value'][1])

    except FileNotFoundError:
        logger.warning("ServiceAccount token not found - not running in a pod?")
        return None
    except Exception as e:
        logger.error(f"Prometheus query error: {e}")
        return None


def query_vllm_metrics():
    """Query Prometheus for persistent vLLM metrics that survive pod restarts."""
    global vllm_metrics_cache

    if vllm_metrics_cache['data'] and (time.time() - vllm_metrics_cache['timestamp']) < vllm_metrics_cache['ttl']:
        return vllm_metrics_cache['data']

    try:
        ns = WHISPER_NAMESPACE

        http_requests_total = query_prometheus(
            f'sum(increase(http_requests_total{{namespace="{ns}",handler="/v1/audio/transcriptions",status="2xx"}}[15d]))'
        )

        generation_tokens = query_prometheus(
            f'sum(increase(vllm:generation_tokens_total{{namespace="{ns}"}}[15d]))'
        )

        prompt_tokens = query_prometheus(
            f'sum(increase(vllm:prompt_tokens_total{{namespace="{ns}"}}[15d]))'
        )

        ttft_sum_rate = query_prometheus(
            f'rate(vllm:time_to_first_token_seconds_sum{{namespace="{ns}"}}[5m])'
        )
        ttft_count_rate = query_prometheus(
            f'rate(vllm:time_to_first_token_seconds_count{{namespace="{ns}"}}[5m])'
        )

        e2e_sum_rate = query_prometheus(
            f'rate(vllm:e2e_request_latency_seconds_sum{{namespace="{ns}"}}[5m])'
        )
        e2e_count_rate = query_prometheus(
            f'rate(vllm:e2e_request_latency_seconds_count{{namespace="{ns}"}}[5m])'
        )

        success_stop = query_prometheus(
            f'sum(increase(vllm:request_success_total{{namespace="{ns}",finished_reason="stop"}}[15d]))'
        )
        success_abort = query_prometheus(
            f'sum(increase(vllm:request_success_total{{namespace="{ns}",finished_reason="abort"}}[15d]))'
        )

        result = {}

        if ttft_count_rate and ttft_sum_rate and ttft_count_rate > 0:
            result['avg_ttft_ms'] = int((ttft_sum_rate / ttft_count_rate) * 1000)
        else:
            result['avg_ttft_ms'] = None

        if e2e_count_rate and e2e_sum_rate and e2e_count_rate > 0:
            result['avg_e2e_ms'] = int((e2e_sum_rate / e2e_count_rate) * 1000)
        else:
            result['avg_e2e_ms'] = None

        result['generation_tokens'] = int(generation_tokens) if generation_tokens else 0
        result['prompt_tokens'] = int(prompt_tokens) if prompt_tokens else 0
        result['http_requests_total'] = int(http_requests_total) if http_requests_total else 0

        stop_count = success_stop or 0
        abort_count = success_abort or 0
        total = stop_count + abort_count
        if total > 0:
            result['success_rate'] = int((stop_count / total) * 100)
        else:
            result['success_rate'] = 100

        vllm_metrics_cache['data'] = result
        vllm_metrics_cache['timestamp'] = time.time()

        logger.debug(f"vLLM metrics (from Prometheus): {result}")
        return result

    except Exception as e:
        logger.error(f"Error querying vLLM metrics from Prometheus: {e}")
        return None

def discover_dcgm_exporter_url():
    """
    Dynamically discover the DCGM exporter URL by:
    1. Finding the Whisper model pod's node
    2. Finding the DCGM exporter pod on that same node
    3. Returning the metrics URL

    This ensures metrics always come from the correct GPU, even if pods reschedule.
    """
    global dcgm_url_cache

    # Check cache
    if dcgm_url_cache['url'] and (time.time() - dcgm_url_cache['timestamp']) < dcgm_url_cache['ttl']:
        return dcgm_url_cache['url']

    if not k8s_v1:
        # Fallback to ConfigMap value if K8s client not available
        logger.warning("Kubernetes client not available, using ConfigMap DCGM_EXPORTER_URL")
        return DCGM_EXPORTER_URL

    try:
        # Find Whisper model pod using WHISPER_MODEL_NAME from ConfigMap
        whisper_pods = k8s_v1.list_namespaced_pod(
            namespace=WHISPER_NAMESPACE,
            label_selector=f'serving.kserve.io/inferenceservice={WHISPER_MODEL_NAME}'
        )

        if not whisper_pods.items:
            logger.error(f"No {WHISPER_MODEL_NAME} pod found, using fallback DCGM URL")
            return DCGM_EXPORTER_URL

        whisper_node = whisper_pods.items[0].spec.node_name
        logger.info(f"Found {WHISPER_MODEL_NAME} pod on node: {whisper_node}")

        # Find DCGM exporter pod on that node
        dcgm_pods = k8s_v1.list_namespaced_pod(
            namespace='nvidia-gpu-operator',
            label_selector='app=nvidia-dcgm-exporter',
            field_selector=f'spec.nodeName={whisper_node}'
        )

        if not dcgm_pods.items:
            logger.error(f"No DCGM exporter pod found on node {whisper_node}")
            return DCGM_EXPORTER_URL

        dcgm_pod_ip = dcgm_pods.items[0].status.pod_ip
        dcgm_url = f"http://{dcgm_pod_ip}:9400/metrics"

        # Update cache
        dcgm_url_cache = {
            'url': dcgm_url,
            'timestamp': time.time(),
            'ttl': 300
        }

        logger.info(f"Discovered DCGM exporter URL: {dcgm_url}")
        return dcgm_url

    except Exception as e:
        logger.error(f"Error discovering DCGM exporter: {e}. Using fallback URL.")
        return DCGM_EXPORTER_URL

@app.route('/')
def index():
    """Interactive voice challenge game (for conferences)"""
    return render_template('index.html',
                         languages=SUPPORTED_LANGUAGES,
                         model_display_name=MODEL_DISPLAY_NAME,
                         conference_name=CONFERENCE_NAME,
                         required_language=REQUIRED_CHALLENGE_LANGUAGE,
                         challenge_count=CHALLENGE_COUNT,
                         win_threshold=WIN_THRESHOLD,
                         challenge_phrases=CHALLENGE_PHRASES)

@app.route('/logo.svg')
def logo():
    from flask import send_file
    import os
    logo_path = os.path.join(os.path.dirname(__file__), 'docs', 'logo.svg')
    return send_file(logo_path, mimetype='image/svg+xml')

@app.route('/architecture')
def architecture():
    from flask import send_file
    import os
    diagram_path = os.path.join(os.path.dirname(__file__), 'docs', 'architecture-diagram.html')
    return send_file(diagram_path)

@app.route('/transcribe-stream', methods=['POST'])
def transcribe_stream():
    """Streaming transcription endpoint"""
    request_id = os.urandom(4).hex()
    logger.info(f"[{request_id}] New STREAMING transcription request")

    if 'audio' not in request.files:
        logger.warning(f"[{request_id}] No audio file in request")
        return jsonify({'error': 'No audio file provided'}), 400

    audio_file = request.files['audio']
    language = request.form.get('language', 'en')
    mode = request.form.get('mode', 'transcriptions')

    logger.info(f"[{request_id}] Request params - mode: {mode}, language: {language}")

    # Determine endpoint based on mode
    endpoint = WHISPER_API_URL.rsplit('/', 1)[0] + '/' + mode
    logger.info(f"[{request_id}] Using endpoint: {endpoint}")

    temp_input_path = None

    try:
        # Determine file extension
        filename = audio_file.filename or 'audio.wav'
        file_ext = os.path.splitext(filename)[1] or '.wav'
        logger.info(f"[{request_id}] Received file: {filename}, MIME: {audio_file.content_type}")

        # Read all audio data
        audio_data = audio_file.read()
        if len(audio_data) == 0:
            logger.error(f"[{request_id}] Received empty audio file")
            return jsonify({'error': 'Received empty audio file'}), 400

        logger.info(f"[{request_id}] Received {len(audio_data)} bytes of audio data")

        # Save to temporary file
        temp_input_path = tempfile.mktemp(suffix=file_ext)
        with open(temp_input_path, 'wb') as f:
            f.write(audio_data)

        logger.info(f"[{request_id}] Saved to: {temp_input_path}")

        # Prepare form data for streaming request
        with open(temp_input_path, 'rb') as f:
            files = {'file': (filename, f, 'audio/wav')}
            data = {
                'model': WHISPER_MODEL_NAME,
                'response_format': 'json',
                'stream': 'true',  # Enable streaming
                'stream_include_usage': 'true'
            }

            # Only add language for transcriptions
            if mode == 'transcriptions':
                data['language'] = language

            logger.info(f"[{request_id}] Sending streaming request to Whisper API...")

            # Make streaming request
            response = requests.post(
                endpoint,
                files=files,
                data=data,
                stream=True,  # Enable streaming
                verify=False
            )

        logger.info(f"[{request_id}] Whisper API response: status={response.status_code}, headers={dict(response.headers)}")

        if response.status_code != 200:
            error_text = response.text
            logger.error(f"[{request_id}] Whisper API error: {error_text}")
            return jsonify({'error': f'Whisper API error: {error_text}'}), response.status_code

        # Stream the response to client
        def generate():
            global last_chunk_metrics
            try:
                line_count = 0
                token_count = 0
                start_time = time.time()

                for line in response.iter_lines():
                    if line:
                        line_count += 1
                        decoded_line = line.decode('utf-8')
                        logger.info(f"[{request_id}] Streaming line {line_count}: {decoded_line}")

                        # vLLM sends SSE format: "data: {...}"
                        if decoded_line.startswith('data: '):
                            json_str = decoded_line[6:]  # Remove "data: " prefix

                            # Check for [DONE] marker
                            if json_str.strip() == '[DONE]':
                                logger.info(f"[{request_id}] Stream completed")

                                # Update metrics
                                duration_ms = (time.time() - start_time) * 1000
                                last_chunk_metrics = {
                                    'tokens': token_count,
                                    'duration_ms': duration_ms,
                                    'timestamp': time.time()
                                }
                                logger.info(f"[{request_id}] Metrics: {token_count} tokens in {duration_ms:.0f}ms")

                                # Track last request time for activity indicator
                                global last_request_time
                                last_request_time = time.time()

                                yield f"data: {json.dumps({'done': True})}\n\n"
                                break

                            try:
                                # Parse the chunk
                                chunk_data = json.loads(json_str)
                                logger.info(f"[{request_id}] Received chunk: {chunk_data}")

                                # Extract text from choices[0].delta.content
                                if 'choices' in chunk_data and len(chunk_data['choices']) > 0:
                                    delta = chunk_data['choices'][0].get('delta', {})
                                    content = delta.get('content', '')
                                    if content:
                                        # Count tokens (approximate: split by space/char)
                                        token_count += len(content.split())

                                        # Send simple format to frontend
                                        yield f"data: {json.dumps({'text': content})}\n\n"
                                        logger.info(f"[{request_id}] Sent to frontend: {content}")
                            except json.JSONDecodeError:
                                logger.warning(f"[{request_id}] Failed to parse JSON: {json_str}")
                        else:
                            # Might be regular JSON response (non-streaming)
                            try:
                                result = json.loads(decoded_line)
                                logger.info(f"[{request_id}] Got non-streaming JSON response: {result}")
                                # Convert to SSE format
                                if 'text' in result:
                                    yield f"data: {json.dumps({'text': result['text']})}\n\n"
                                    yield f"data: {json.dumps({'done': True})}\n\n"
                                    break
                            except json.JSONDecodeError:
                                # Forward as-is
                                yield f"{decoded_line}\n"

                logger.info(f"[{request_id}] Total lines processed: {line_count}")
            finally:
                # Cleanup
                if temp_input_path and os.path.exists(temp_input_path):
                    os.unlink(temp_input_path)
                    logger.debug(f"[{request_id}] Cleaned up temp file")

        return Response(
            stream_with_context(generate()),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no'
            }
        )

    except Exception as e:
        logger.exception(f"[{request_id}] Transcription failed: {e}")
        # Cleanup
        if temp_input_path and os.path.exists(temp_input_path):
            os.unlink(temp_input_path)
        return jsonify({'error': str(e)}), 500

def query_dcgm_metric(metric_name):
    """Query DCGM exporter for GPU metrics.

    Dynamically discovers the correct DCGM exporter for the Whisper model's GPU.
    Falls back to any GPU metric if Whisper is idle.
    """
    try:
        # Get the correct DCGM exporter URL (auto-discovered or cached)
        dcgm_url = discover_dcgm_exporter_url()

        response = requests.get(
            dcgm_url,
            timeout=2  # Fast timeout for real-time feel
        )

        if response.status_code == 200:
            # Parse Prometheus text format
            # Example line: DCGM_FI_DEV_FB_USED{gpu="0",UUID="...",namespace="whisper"} 14653
            whisper_value = None
            fallback_value = None

            for line in response.text.split('\n'):
                if line.startswith(metric_name + '{'):
                    parts = line.split()
                    if len(parts) >= 2:
                        value = float(parts[-1])

                        # Prefer whisper namespace
                        if 'namespace="whisper"' in line:
                            logger.debug(f"DCGM metric {metric_name} from whisper: {value}")
                            return value

                        # Store first metric as fallback
                        if fallback_value is None:
                            fallback_value = value

            # Use fallback if whisper metric not found (whisper idle)
            if fallback_value is not None:
                logger.debug(f"DCGM metric {metric_name} fallback: {fallback_value}")
                return fallback_value

        logger.warning(f"DCGM metric {metric_name} not found")
        return None

    except Exception as e:
        logger.error(f"DCGM query error for {metric_name}: {e}")
        return None

@app.route('/metrics', methods=['GET'])
def get_metrics():
    """Return GPU metrics for real-time dashboard (queries DCGM exporter directly)"""
    global last_chunk_metrics, gpu_util_history, last_gpu_sample_time, last_request_time

    try:
        # Query DCGM exporter directly for real-time GPU metrics
        # Show ANY GPU activity (not filtered by namespace) for conference demo
        # This ensures metrics are visible even when Whisper is idle

        # VRAM (in MB, convert to GB)
        vram_used_mb = query_dcgm_metric('DCGM_FI_DEV_FB_USED')
        vram_free_mb = query_dcgm_metric('DCGM_FI_DEV_FB_FREE')

        vram_used = round(vram_used_mb / 1024, 1) if vram_used_mb else 0
        vram_free = round(vram_free_mb / 1024, 1) if vram_free_mb else 0
        vram_total = round(vram_used + vram_free, 1) if (vram_used and vram_free) else 46.0

        # Temperature
        temperature = query_dcgm_metric('DCGM_FI_DEV_GPU_TEMP')
        temperature = int(temperature) if temperature else 0

        # GPU Utilization - build histogram over last 60 seconds
        current_gpu_util = query_dcgm_metric('DCGM_FI_DEV_GPU_UTIL')
        current_gpu_util = int(current_gpu_util) if current_gpu_util else 0

        # Sample once per second (frontend polls every 2s, but we want consistent history)
        now = time.time()
        if now - last_gpu_sample_time >= 1.0:
            gpu_util_history.append(current_gpu_util)
            last_gpu_sample_time = now

        # Calculate peak and average from history
        if len(gpu_util_history) > 0:
            gpu_util_peak = max(gpu_util_history)
            gpu_util_avg = sum(gpu_util_history) // len(gpu_util_history)
        else:
            gpu_util_peak = current_gpu_util
            gpu_util_avg = current_gpu_util

        # Convert deque to list for JSON serialization
        gpu_util_history_list = list(gpu_util_history)

        # Tokens/sec from our tracking (persists until next player)
        tokens_per_sec = 0
        if last_chunk_metrics['duration_ms'] > 0:
            # Calculate tokens/second from last chunk
            tokens_per_sec = int(
                (last_chunk_metrics['tokens'] / last_chunk_metrics['duration_ms']) * 1000
            )

        # KV cache usage (real-time gauge from vLLM, not DCGM)
        kv_cache_usage = query_vllm_gauge('vllm:kv_cache_usage_perc')
        kv_cache_pct = round(kv_cache_usage * 100, 1) if kv_cache_usage is not None else 0

        # Calculate seconds since last activity
        seconds_since_last = int(time.time() - last_request_time) if last_request_time > 0 else 0

        # Query vLLM metrics
        vllm_metrics = query_vllm_metrics()
        if vllm_metrics:
            avg_ttft_ms = vllm_metrics.get('avg_ttft_ms')
            avg_e2e_ms = vllm_metrics.get('avg_e2e_ms')
            generation_tokens = vllm_metrics.get('generation_tokens', 0)
            prompt_tokens = vllm_metrics.get('prompt_tokens', 0)
            success_rate = vllm_metrics.get('success_rate', 100)
            http_requests_total = vllm_metrics.get('http_requests_total', 0)
        else:
            avg_ttft_ms = None
            avg_e2e_ms = None
            generation_tokens = 0
            prompt_tokens = 0
            success_rate = 100
            http_requests_total = 0

        metrics = {
            'vram_used': vram_used,
            'vram_total': vram_total,
            'temperature': temperature,
            'tokens_per_sec': tokens_per_sec,
            'gpu_util': current_gpu_util,
            'gpu_util_peak': gpu_util_peak,
            'gpu_util_avg': gpu_util_avg,
            'gpu_util_history': gpu_util_history_list,
            'requests_processed': http_requests_total,  # vLLM source of truth
            'last_activity_seconds': seconds_since_last,
            # vLLM metrics
            'vllm_avg_ttft_ms': avg_ttft_ms,
            'vllm_avg_e2e_ms': avg_e2e_ms,
            'vllm_generation_tokens': generation_tokens,
            'vllm_prompt_tokens': prompt_tokens,
            'vllm_success_rate': success_rate,
            'kv_cache_usage_pct': kv_cache_pct,
            'model': WHISPER_MODEL_NAME
        }

        logger.debug(f"Metrics: {metrics}")
        return jsonify(metrics)

    except Exception as e:
        logger.error(f"Error fetching metrics: {e}")
        # Return empty metrics rather than failing
        return jsonify({
            'vram_used': 0,
            'vram_total': 46,
            'temperature': 0,
            'tokens_per_sec': 0,
            'gpu_util': 0,
            'gpu_util_peak': 0,
            'gpu_util_avg': 0,
            'gpu_util_history': [],
            'requests_processed': 0,
            'last_activity_seconds': 0,
            'vllm_avg_ttft_ms': None,
            'vllm_avg_e2e_ms': None,
            'vllm_generation_tokens': 0,
            'vllm_prompt_tokens': 0,
            'vllm_success_rate': 100,
            'kv_cache_usage_pct': 0,
            'model': WHISPER_MODEL_NAME
        })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
