# Whisper Voice Challenge — Final Statistics

**Innovate Together Sibenik | October 13–14, 2026**

## Overview

The Whisper Voice Challenge is an interactive AI-powered game where conference attendees speak challenge phrases in various languages and an on-premise Whisper AI model transcribes their speech in real time. Players are scored on transcription accuracy across multiple languages — the more accurate the AI can understand them, the higher they score.

The game ran on Red Hat OpenShift AI with a fully on-premise deployment — no cloud APIs, no data leaving the cluster.

## Key Numbers

| Metric | Value |
|--------|-------|
| Registered players | 145 |
| Completed games | 214 |
| Total voice attempts | 1,104 |
| Perfect transcriptions (99%+) | 268 (24.3%) |
| Languages tested | 29 |
| Returning players (2+ games) | 27 (19%) |

## Accuracy by Language

### Top 5 — Easiest for Whisper

| Language | Avg Accuracy | Attempts |
|----------|-------------|----------|
| English | 97.0% | 16 |
| Portuguese | 93.9% | 52 |
| Italian | 93.5% | 47 |
| Romanian | 92.5% | 55 |
| Spanish | 90.5% | 19 |

### Bottom 5 — Toughest for Humans

| Language | Avg Accuracy | Attempts |
|----------|-------------|----------|
| Japanese | 6.7% | 23 |
| Thai | 13.0% | 29 |
| Georgian | 15.3% | 5 |
| Chinese | 16.0% | 20 |
| Korean | 18.1% | 23 |

### All 29 Languages

| Language | Avg Accuracy | Max Accuracy | Attempts |
|----------|-------------|-------------|----------|
| English | 97.0% | 100% | 16 |
| Portuguese | 93.9% | 100% | 52 |
| Italian | 93.5% | 100% | 47 |
| Romanian | 92.5% | 100% | 55 |
| Spanish | 90.5% | 100% | 19 |
| German | 90.4% | 100% | 20 |
| Swedish | 89.5% | 100% | 45 |
| Croatian | 89.3% | 100% | 241 |
| Slovak | 89.0% | 100% | 20 |
| Slovenian | 88.9% | 96.4% | 3 |
| Dutch | 88.2% | 100% | 72 |
| French | 86.2% | 100% | 18 |
| Czech | 86.2% | 100% | 13 |
| Serbian | 85.1% | 100% | 25 |
| Norwegian | 79.7% | 100% | 59 |
| Hungarian | 79.6% | 100% | 16 |
| Polish | 74.8% | 100% | 21 |
| Turkish | 69.5% | 100% | 51 |
| Finnish | 69.2% | 100% | 52 |
| Icelandic | 64.4% | 91.7% | 61 |
| Ukrainian | 56.4% | 97.7% | 54 |
| Bulgarian | 52.7% | 80.7% | 8 |
| Arabic | 26.7% | 52.6% | 17 |
| Hindi | 18.8% | 37.9% | 19 |
| Korean | 18.1% | 55.0% | 23 |
| Chinese | 16.0% | 60.0% | 20 |
| Georgian | 15.3% | 21.6% | 5 |
| Thai | 13.0% | 37.1% | 29 |
| Japanese | 6.7% | 26.9% | 23 |

## Winners

| Rank | Player | Score | Difficulty |
|------|--------|-------|------------|
| 1st | Lukas | 164.5 | Hard |
| 2nd | Sindy | 163.9 | Hard |
| 3rd | Rammstein | 163.8 | Medium |
| 4th | rasto | 159.8 | Medium |
| 5th | Hbz | 158.2 | Medium |
| 6th | Vedran | 155.9 | Medium |
| 7th | AndrejG | 155.1 | Medium |

## Engagement

- **Most dedicated players**: Hbz (13 games), rasto (12 games), Sindy, Bru, and Ovca (7 games each)
- **Most attempted language**: Croatian with 241 attempts (hosted in Sibenik, Croatia)
- **Difficulty split**: 143 medium games (67%), 64 hard games (30%), 7 easy games (3%)
- **80% of players** played exactly once — typical booth drop-in pattern
- **19% came back** for a second (or third, or thirteenth) round

## Technical Setup

- **Model**: RedHat AI Whisper large-v3 (809M parameters)
- **Platform**: OpenShift AI on a single-node AWS cluster (g6.16xlarge, 1x NVIDIA L4 GPU)
- **Inference**: vLLM serving engine, fully on-premise — no cloud APIs
- **Scoring**: Server-side Levenshtein similarity between spoken transcription and reference phrase
