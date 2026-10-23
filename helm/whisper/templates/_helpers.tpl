{{- define "whisper-ui.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "whisper-ui.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{- define "whisper-ui.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "whisper-ui.labels" -}}
helm.sh/chart: {{ include "whisper-ui.chart" . }}
{{ include "whisper-ui.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{- define "whisper-ui.selectorLabels" -}}
app: whisper-ui
app.kubernetes.io/name: {{ include "whisper-ui.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{- define "whisper-ui.namespace" -}}
{{- default .Release.Namespace .Values.namespace }}
{{- end }}

{{/* Resolve once per render so the Secret and pod checksum use the same keys.
     lookup requires a server-side Helm upgrade; offline rendering generates keys. */}}
{{- define "whisper-ui.credentials" -}}
{{- if not (hasKey .Values "_resolvedCredentials") -}}
{{- $existing := (lookup "v1" "Secret" (include "whisper-ui.namespace" .) "whisper-tournament-secret") | default dict -}}
{{- $data := $existing.data | default dict -}}
{{- $secret := .Values.tournament.secret | default (get $data "TOURNAMENT_SECRET" | b64dec) | default (randAlphaNum 48) -}}
{{- $admin := .Values.tournament.adminToken | default (get $data "ADMIN_TOKEN" | b64dec) | default (randAlphaNum 32) -}}
{{- $_ := set .Values "_resolvedCredentials" (dict "TOURNAMENT_SECRET" $secret "ADMIN_TOKEN" $admin) -}}
{{- end -}}
{{- toYaml .Values._resolvedCredentials -}}
{{- end -}}

{{- define "whisper-ui.validate" -}}
{{- $phrases := .Files.Get "challenges.json" | mustFromJson -}}
{{- $pools := .Values.difficultyPools | mustFromJson -}}
{{- $languages := .Values.languageInfo | mustFromJson -}}
{{- $required := .Values.game.requiredLanguage -}}
{{- if not (get $phrases $required) -}}{{ fail "Choose game.requiredLanguage explicitly (installer: --language cs/sk/en); language must have challenge phrases" }}{{- end -}}
{{- if not (get $languages $required) -}}{{ fail "Required language missing from languageInfo" }}{{- end -}}
{{- range $difficulty := list "easy" "medium" "hard" -}}
{{- $pool := get $pools $difficulty -}}
{{- if not $pool -}}{{ fail (printf "Empty difficulty pool: %s" $difficulty) }}{{- end -}}
{{- range $language := $pool -}}
{{- if not (get $phrases $language) -}}{{ fail (printf "No phrases for pool language: %s" $language) }}{{- end -}}
{{- if not (get $languages $language) -}}{{ fail (printf "No languageInfo for: %s" $language) }}{{- end -}}
{{- end -}}
{{- end -}}
{{- if gt (int .Values.game.winThreshold) (int .Values.game.challengeCount) -}}{{ fail "winThreshold cannot exceed challengeCount" }}{{- end -}}
{{- end -}}
