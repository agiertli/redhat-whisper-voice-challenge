from flask import Flask, render_template, request, jsonify, Response, stream_with_context, g
import requests
import os
import tempfile
import json
import logging
import sys
import time
import sqlite3
import hashlib
import hmac
import csv
import io
import re
from functools import wraps
from datetime import datetime, timezone
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


CHALLENGE_PHRASES = json.loads(os.getenv('CHALLENGE_PHRASES',
    '{"en": ["Artificial intelligence transforms business", "Kubernetes simplifies application deployment", "Cloud solutions increase efficiency"]}'))

# Tournament settings
TOURNAMENT_SECRET = os.getenv('TOURNAMENT_SECRET', 'change-me-in-production')
ADMIN_TOKEN = os.getenv('ADMIN_TOKEN', 'admin-change-me')
DB_PATH = os.getenv('DB_PATH', '/app/data/tournament.db')

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

# --- Tournament Database ---

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    db = sqlite3.connect(DB_PATH)
    db.execute('PRAGMA journal_mode=WAL')
    db.executescript('''
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nickname TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id INTEGER NOT NULL REFERENCES players(id),
            difficulty TEXT NOT NULL CHECK(difficulty IN ('easy','medium','hard')),
            started_at TEXT NOT NULL,
            completed_at TEXT,
            total_score REAL,
            avg_accuracy REAL,
            duration_seconds REAL,
            won INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id INTEGER NOT NULL REFERENCES games(id),
            attempt_index INTEGER NOT NULL,
            language TEXT NOT NULL,
            phrase TEXT NOT NULL,
            transcription TEXT,
            accuracy REAL,
            status TEXT NOT NULL CHECK(status IN ('win','fail','skip'))
        );
        CREATE INDEX IF NOT EXISTS idx_games_player ON games(player_id);
        CREATE INDEX IF NOT EXISTS idx_games_score ON games(total_score DESC);
        CREATE INDEX IF NOT EXISTS idx_attempts_game ON attempts(game_id);
    ''')
    db.close()
    logger.info(f"Tournament database initialized at {DB_PATH}")

init_db()


def get_db():
    db = sqlite3.connect(DB_PATH, timeout=10)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA journal_mode=WAL')
    db.execute('PRAGMA foreign_keys=ON')
    return db


def create_token(player_id):
    payload = f"{player_id}:{int(time.time())}"
    sig = hmac.new(TOURNAMENT_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
    import base64
    return base64.urlsafe_b64encode(f"{payload}:{sig}".encode()).decode()


def verify_token(token):
    try:
        import base64
        decoded = base64.urlsafe_b64decode(token.encode()).decode()
        parts = decoded.rsplit(':', 1)
        if len(parts) != 2:
            return None
        payload, sig = parts
        expected = hmac.new(TOURNAMENT_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        player_id = int(payload.split(':')[0])
        return player_id
    except Exception:
        return None


def require_token(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get('Authorization', '')
        if not auth.startswith('Bearer '):
            return jsonify({'error': 'Missing authorization'}), 401
        player_id = verify_token(auth[7:])
        if player_id is None:
            return jsonify({'error': 'Invalid token'}), 401
        g.player_id = player_id
        return f(*args, **kwargs)
    return decorated


def require_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get('Authorization', '')
        if not auth.startswith('Bearer ') or auth[7:] != ADMIN_TOKEN:
            return jsonify({'error': 'Forbidden'}), 403
        return f(*args, **kwargs)
    return decorated


# --- Server-side scoring ---

def normalize_text(text):
    return re.sub(r'\s+', ' ', re.sub(r'[.,!?;:]', '', text.lower().strip()))


def levenshtein_distance(s1, s2):
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)
    prev_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        curr_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = prev_row[j + 1] + 1
            deletions = curr_row[j] + 1
            substitutions = prev_row[j] + (c1 != c2)
            curr_row.append(min(insertions, deletions, substitutions))
        prev_row = curr_row
    return prev_row[-1]


def levenshtein_similarity(s1, s2):
    t = normalize_text(s1)
    e = normalize_text(s2)
    longer = t if len(t) >= len(e) else e
    if len(longer) == 0:
        return 1.0
    dist = levenshtein_distance(t, e)
    return (len(longer) - dist) / len(longer)


def compute_total_score(difficulty, avg_accuracy, duration_seconds):
    multipliers = {'easy': 1.0, 'medium': 1.5, 'hard': 2.0}
    difficulty_mult = multipliers.get(difficulty, 1.0)
    accuracy_pts = avg_accuracy * 100
    speed_bonus = max(0.8, 1.2 - (duration_seconds / 600))
    return round(difficulty_mult * accuracy_pts * speed_bonus, 1)


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
            f'sum(increase(vllm:request_success_total{{namespace="{ns}"}}[15d]))'
        )

        generation_tokens = query_prometheus(
            f'sum(increase(vllm:generation_tokens_total{{namespace="{ns}"}}[15d]))'
        )

        prompt_tokens = query_prometheus(
            f'sum(increase(vllm:prompt_tokens_total{{namespace="{ns}"}}[15d]))'
        )

        ttft_sum = query_prometheus(
            f'sum(increase(vllm:time_to_first_token_seconds_sum{{namespace="{ns}"}}[15d]))'
        )
        ttft_count = query_prometheus(
            f'sum(increase(vllm:time_to_first_token_seconds_count{{namespace="{ns}"}}[15d]))'
        )

        e2e_sum = query_prometheus(
            f'sum(increase(vllm:e2e_request_latency_seconds_sum{{namespace="{ns}"}}[15d]))'
        )
        e2e_count = query_prometheus(
            f'sum(increase(vllm:e2e_request_latency_seconds_count{{namespace="{ns}"}}[15d]))'
        )

        success_stop = query_prometheus(
            f'sum(increase(vllm:request_success_total{{namespace="{ns}",finished_reason="stop"}}[15d]))'
        )
        success_abort = query_prometheus(
            f'sum(increase(vllm:request_success_total{{namespace="{ns}",finished_reason="abort"}}[15d]))'
        )

        result = {}

        if ttft_count and ttft_sum and ttft_count > 0:
            result['avg_ttft_ms'] = int((ttft_sum / ttft_count) * 1000)
        else:
            result['avg_ttft_ms'] = None

        if e2e_count and e2e_sum and e2e_count > 0:
            result['avg_e2e_ms'] = int((e2e_sum / e2e_count) * 1000)
        else:
            result['avg_e2e_ms'] = None

        result['generation_tokens'] = int(generation_tokens) if generation_tokens else 0
        result['prompt_tokens'] = int(prompt_tokens) if prompt_tokens else 0
        result['http_requests_total'] = int(http_requests_total) if http_requests_total else 0

        if generation_tokens and e2e_sum and e2e_sum > 0:
            result['avg_tokens_per_sec'] = int(generation_tokens / e2e_sum)
        else:
            result['avg_tokens_per_sec'] = 0

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
    logo_path = os.path.join(os.path.dirname(__file__), 'docs', 'navbar.svg')
    return send_file(logo_path, mimetype='image/svg+xml')

@app.route('/favicon.svg')
def favicon():
    from flask import send_file
    import os
    favicon_path = os.path.join(os.path.dirname(__file__), 'docs', 'favicon.svg')
    return send_file(favicon_path, mimetype='image/svg+xml')

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

        # Tokens/sec from Prometheus (lifetime average, multi-worker safe)
        tokens_per_sec = 0

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
            tokens_per_sec = vllm_metrics.get('avg_tokens_per_sec', 0)
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

# --- Tournament API ---

@app.route('/api/register', methods=['POST'])
def api_register():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'JSON body required'}), 400

    nickname = (data.get('nickname') or '').strip()
    name = (data.get('name') or '').strip()
    email = (data.get('email') or '').strip()

    if not nickname or len(nickname) < 2 or len(nickname) > 20:
        return jsonify({'error': 'Nickname must be 2-20 characters'}), 400
    if not re.match(r'^[a-zA-Z0-9_-]+$', nickname):
        return jsonify({'error': 'Nickname: letters, numbers, underscores, hyphens only'}), 400
    if not name or len(name) < 2:
        return jsonify({'error': 'Name is required (min 2 characters)'}), 400
    if not email or '@' not in email:
        return jsonify({'error': 'Valid email is required'}), 400

    db = get_db()
    try:
        db.execute('INSERT INTO players (nickname, name, email) VALUES (?, ?, ?)',
                   (nickname, name, email))
        db.commit()
        player_id = db.execute('SELECT id FROM players WHERE nickname = ?', (nickname,)).fetchone()['id']
        token = create_token(player_id)
        return jsonify({'player_id': player_id, 'nickname': nickname, 'token': token}), 201
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Nickname already taken'}), 409
    finally:
        db.close()


@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'JSON body required'}), 400

    nickname = (data.get('nickname') or '').strip()
    email = (data.get('email') or '').strip()

    if not nickname or not email:
        return jsonify({'error': 'Nickname and email are required'}), 400

    db = get_db()
    try:
        player = db.execute(
            'SELECT id, nickname FROM players WHERE nickname = ? AND email = ?',
            (nickname, email)).fetchone()
        if not player:
            return jsonify({'error': 'No account found with that nickname and email'}), 404
        token = create_token(player['id'])
        return jsonify({'player_id': player['id'], 'nickname': player['nickname'], 'token': token})
    finally:
        db.close()


@app.route('/api/player/me', methods=['GET'])
@require_token
def api_player_me():
    db = get_db()
    try:
        player = db.execute('SELECT id, nickname, created_at FROM players WHERE id = ?',
                           (g.player_id,)).fetchone()
        if not player:
            return jsonify({'error': 'Player not found'}), 404
        best = db.execute('SELECT MAX(total_score) as best_score FROM games WHERE player_id = ? AND total_score IS NOT NULL',
                         (g.player_id,)).fetchone()
        games_played = db.execute('SELECT COUNT(*) as count FROM games WHERE player_id = ? AND completed_at IS NOT NULL',
                                 (g.player_id,)).fetchone()['count']
        return jsonify({
            'player_id': player['id'],
            'nickname': player['nickname'],
            'best_score': best['best_score'] if best else None,
            'games_played': games_played
        })
    finally:
        db.close()


@app.route('/api/game/start', methods=['POST'])
@require_token
def api_game_start():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'JSON body required'}), 400

    difficulty = data.get('difficulty')
    if difficulty not in ('easy', 'medium', 'hard'):
        return jsonify({'error': 'Invalid difficulty'}), 400

    started_at = datetime.now(timezone.utc).isoformat()
    db = get_db()
    try:
        cursor = db.execute(
            'INSERT INTO games (player_id, difficulty, started_at) VALUES (?, ?, ?)',
            (g.player_id, difficulty, started_at))
        db.commit()
        return jsonify({
            'game_id': cursor.lastrowid,
            'difficulty': difficulty,
            'started_at': started_at
        }), 201
    finally:
        db.close()


@app.route('/api/game/<int:game_id>/attempt', methods=['POST'])
@require_token
def api_game_attempt(game_id):
    data = request.get_json()
    if not data:
        return jsonify({'error': 'JSON body required'}), 400

    db = get_db()
    try:
        game = db.execute('SELECT * FROM games WHERE id = ? AND player_id = ?',
                         (game_id, g.player_id)).fetchone()
        if not game:
            return jsonify({'error': 'Game not found'}), 404
        if game['completed_at']:
            return jsonify({'error': 'Game already completed'}), 400

        attempt_index = data.get('attempt_index')
        language = data.get('language', '')
        phrase = data.get('phrase', '')
        transcription = data.get('transcription', '')
        status = data.get('status', 'completed')

        if attempt_index is None or not isinstance(attempt_index, int) or attempt_index < 0:
            return jsonify({'error': 'Invalid attempt_index'}), 400

        existing = db.execute('SELECT id FROM attempts WHERE game_id = ? AND attempt_index = ?',
                             (game_id, attempt_index)).fetchone()
        if existing:
            return jsonify({'error': 'Attempt already submitted'}), 400

        lang_phrases = CHALLENGE_PHRASES.get(language, [])
        if phrase not in lang_phrases and status != 'skip':
            return jsonify({'error': 'Invalid phrase for language'}), 400

        if status == 'skip':
            skip_count = db.execute(
                "SELECT COUNT(*) as cnt FROM attempts WHERE game_id = ? AND status = 'skip'",
                (game_id,)).fetchone()['cnt']
            if skip_count >= 1:
                return jsonify({'error': 'Maximum 1 skip per game'}), 400
            accuracy = 0.0
            result_status = 'skip'
        else:
            accuracy = levenshtein_similarity(transcription, phrase)
            result_status = 'win' if accuracy >= 0.80 else 'fail'

        db.execute(
            'INSERT INTO attempts (game_id, attempt_index, language, phrase, transcription, accuracy, status) VALUES (?, ?, ?, ?, ?, ?, ?)',
            (game_id, attempt_index, language, phrase, transcription, round(accuracy, 4), result_status))
        db.commit()

        return jsonify({'accuracy': round(accuracy, 4), 'status': result_status})
    finally:
        db.close()


@app.route('/api/game/<int:game_id>/complete', methods=['POST'])
@require_token
def api_game_complete(game_id):
    db = get_db()
    try:
        game = db.execute('SELECT * FROM games WHERE id = ? AND player_id = ?',
                         (game_id, g.player_id)).fetchone()
        if not game:
            return jsonify({'error': 'Game not found'}), 404
        if game['completed_at']:
            return jsonify({'error': 'Game already completed'}), 400

        completed_at = datetime.now(timezone.utc).isoformat()
        started_dt = datetime.fromisoformat(game['started_at'])
        completed_dt = datetime.fromisoformat(completed_at)
        duration_seconds = (completed_dt - started_dt).total_seconds()

        attempts = db.execute('SELECT * FROM attempts WHERE game_id = ?', (game_id,)).fetchall()
        scored = [a for a in attempts if a['status'] != 'skip']
        avg_accuracy = sum(a['accuracy'] for a in scored) / len(scored) if scored else 0.0
        won = 1 if avg_accuracy >= 0.80 else 0
        total_score = compute_total_score(game['difficulty'], avg_accuracy, duration_seconds)

        db.execute('''UPDATE games SET completed_at=?, total_score=?, avg_accuracy=?,
                      duration_seconds=?, won=? WHERE id=?''',
                   (completed_at, total_score, round(avg_accuracy, 4),
                    round(duration_seconds, 1), won, game_id))
        db.commit()

        best_row = db.execute('SELECT MAX(total_score) as best FROM games WHERE player_id = ? AND completed_at IS NOT NULL',
                             (g.player_id,)).fetchone()
        best_score = best_row['best'] if best_row else total_score
        is_new_best = total_score >= best_score

        rank_row = db.execute('''
            SELECT COUNT(*) + 1 as rank FROM (
                SELECT player_id, MAX(total_score) as best
                FROM games WHERE completed_at IS NOT NULL AND total_score IS NOT NULL
                GROUP BY player_id
            ) WHERE best > ?''', (best_score,)).fetchone()
        rank = rank_row['rank'] if rank_row else 1

        return jsonify({
            'total_score': total_score,
            'avg_accuracy': round(avg_accuracy, 4),
            'duration_seconds': round(duration_seconds, 1),
            'difficulty': game['difficulty'],
            'won': bool(won),
            'rank': rank,
            'best_score': best_score,
            'is_new_best': is_new_best
        })
    finally:
        db.close()


@app.route('/api/leaderboard', methods=['GET'])
def api_leaderboard():
    limit = min(int(request.args.get('limit', 20)), 100)
    db = get_db()
    try:
        rows = db.execute('''
            SELECT p.nickname, g.total_score, g.difficulty, g.avg_accuracy, g.duration_seconds
            FROM games g
            JOIN players p ON p.id = g.player_id
            WHERE g.completed_at IS NOT NULL AND g.total_score IS NOT NULL
            AND g.id = (
                SELECT g2.id FROM games g2
                WHERE g2.player_id = g.player_id AND g2.completed_at IS NOT NULL
                ORDER BY g2.total_score DESC LIMIT 1
            )
            GROUP BY g.player_id
            ORDER BY g.total_score DESC
            LIMIT ?
        ''', (limit,)).fetchall()

        total_players = db.execute('SELECT COUNT(DISTINCT player_id) as cnt FROM games WHERE completed_at IS NOT NULL').fetchone()['cnt']

        leaderboard = []
        for i, row in enumerate(rows):
            leaderboard.append({
                'rank': i + 1,
                'nickname': row['nickname'],
                'score': row['total_score'],
                'difficulty': row['difficulty'],
                'avg_accuracy': round(row['avg_accuracy'] * 100, 1) if row['avg_accuracy'] else 0,
                'duration_seconds': round(row['duration_seconds'], 1) if row['duration_seconds'] else 0
            })

        return jsonify({
            'leaderboard': leaderboard,
            'total_players': total_players,
            'updated_at': datetime.now(timezone.utc).isoformat()
        })
    finally:
        db.close()


@app.route('/api/admin/players', methods=['GET'])
@require_admin
def api_admin_players():
    db = get_db()
    try:
        rows = db.execute('''
            SELECT p.id, p.nickname, p.name, p.email, p.created_at,
                   MAX(g.total_score) as best_score,
                   COUNT(CASE WHEN g.completed_at IS NOT NULL THEN 1 END) as games_played
            FROM players p
            LEFT JOIN games g ON g.player_id = p.id
            GROUP BY p.id
            ORDER BY best_score DESC NULLS LAST
        ''').fetchall()

        players = []
        for row in rows:
            players.append({
                'id': row['id'],
                'nickname': row['nickname'],
                'name': row['name'],
                'email': row['email'],
                'best_score': row['best_score'],
                'games_played': row['games_played'],
                'created_at': row['created_at']
            })

        return jsonify({'players': players})
    finally:
        db.close()


@app.route('/api/admin/export', methods=['GET'])
def api_admin_export():
    auth = request.headers.get('Authorization', '')
    token_param = request.args.get('token', '')
    if not ((auth.startswith('Bearer ') and auth[7:] == ADMIN_TOKEN) or token_param == ADMIN_TOKEN):
        return jsonify({'error': 'Forbidden'}), 403
    db = get_db()
    try:
        rows = db.execute('''
            SELECT p.nickname, p.name, p.email,
                   MAX(g.total_score) as best_score, g.difficulty,
                   COUNT(CASE WHEN g.completed_at IS NOT NULL THEN 1 END) as games_played
            FROM players p
            LEFT JOIN games g ON g.player_id = p.id
            GROUP BY p.id
            ORDER BY best_score DESC NULLS LAST
        ''').fetchall()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['rank', 'nickname', 'name', 'email', 'best_score', 'difficulty', 'games_played'])
        for i, row in enumerate(rows):
            writer.writerow([i + 1, row['nickname'], row['name'], row['email'],
                           row['best_score'] or 0, row['difficulty'] or '', row['games_played']])

        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': 'attachment; filename=tournament_results.csv'}
        )
    finally:
        db.close()


@app.route('/api/admin/players/<int:player_id>/games', methods=['GET'])
@require_admin
def api_admin_player_games(player_id):
    db = get_db()
    try:
        games = db.execute('''
            SELECT id, difficulty, total_score, avg_accuracy, duration_seconds,
                   started_at, completed_at, won
            FROM games WHERE player_id = ? AND completed_at IS NOT NULL
            ORDER BY total_score DESC
        ''', (player_id,)).fetchall()

        return jsonify({'games': [{
            'id': g['id'],
            'difficulty': g['difficulty'],
            'score': g['total_score'],
            'accuracy': round((g['avg_accuracy'] or 0) * 100, 1),
            'duration': round(g['duration_seconds'] or 0, 1),
            'started_at': g['started_at'],
            'completed_at': g['completed_at'],
            'won': bool(g['won'])
        } for g in games]})
    finally:
        db.close()


@app.route('/api/admin/export-games', methods=['GET'])
def api_admin_export_games():
    auth = request.headers.get('Authorization', '')
    token_param = request.args.get('token', '')
    if not ((auth.startswith('Bearer ') and auth[7:] == ADMIN_TOKEN) or token_param == ADMIN_TOKEN):
        return jsonify({'error': 'Forbidden'}), 403
    db = get_db()
    try:
        rows = db.execute('''
            SELECT p.nickname, p.name, p.email,
                   g.id as game_id, g.difficulty, g.total_score, g.avg_accuracy,
                   g.duration_seconds, g.started_at, g.completed_at, g.won
            FROM games g
            JOIN players p ON p.id = g.player_id
            WHERE g.completed_at IS NOT NULL
            ORDER BY g.total_score DESC
        ''').fetchall()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['nickname', 'name', 'email', 'game_id', 'difficulty', 'score',
                        'accuracy_%', 'duration_s', 'started_at', 'completed_at', 'won'])
        for row in rows:
            writer.writerow([row['nickname'], row['name'], row['email'],
                           row['game_id'], row['difficulty'], row['total_score'] or 0,
                           round((row['avg_accuracy'] or 0) * 100, 1),
                           round(row['duration_seconds'] or 0, 1),
                           row['started_at'], row['completed_at'],
                           'yes' if row['won'] else 'no'])

        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': 'attachment; filename=tournament_all_games.csv'}
        )
    finally:
        db.close()


@app.route('/api/admin/reset-scores', methods=['POST'])
@require_admin
def api_admin_reset_scores():
    db = get_db()
    try:
        db.execute('DELETE FROM attempts')
        db.execute('DELETE FROM games')
        db.commit()
        return jsonify({'message': 'All games and attempts deleted', 'players_kept': True})
    finally:
        db.close()


@app.route('/admin')
def admin_page():
    return render_template('admin.html')


@app.route('/tv')
def tv_page():
    return render_template('tv.html', conference_name=CONFERENCE_NAME)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
