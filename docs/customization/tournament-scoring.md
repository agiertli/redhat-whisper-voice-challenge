# Tournament scoring

These are the rules implemented in `src/app_streaming.py`
(`normalize_text`, `levenshtein_similarity`, `compute_total_score`, game attempt
and completion endpoints). Both registration modes use the same formula.
The server computes and persists accuracy, elapsed time and the final score.

## Accuracy for one attempt

Normalize the transcript and expected phrase by lowercasing, trimming leading and
trailing whitespace, removing `. , ! ? ; :`, and collapsing whitespace to one
space. Accents and other characters are retained: this is character similarity,
not word error rate or semantic similarity.

```text
accuracy = 1 - LevenshteinDistance(transcript, phrase)
                 / max(length(transcript), length(phrase))
```

Lengths and distance use normalized strings. Accuracy ranges from 0 to 1; two
empty normalized strings score 1. Each submitted accuracy is stored rounded to
four decimal places. An attempt is a win at accuracy >= 0.80; below that it is a
fail. A failed attempt still contributes its actual accuracy to the average.

## Final score

```text
average_accuracy = mean(stored accuracies of all scored attempts)
speed_bonus      = max(0.8, 1.2 - elapsed_seconds / 600)
score            = round(difficulty_multiplier * average_accuracy * 100
                         * speed_bonus, 1)
```

- Easy multiplier: **1.0**.
- Medium multiplier: **1.5**.
- Hard multiplier: **2.0**.
- Elapsed time is measured by the server from game creation to completion. It
  includes pauses, challenge transitions and swaps, not just microphone time.
- Speed bonus starts near 1.2, equals 1.0 at 120 seconds, reaches 0.8 at 240 seconds,
  and stays at 0.8 for longer games. The theoretical zero-time maxima for perfect
  accuracy are 120 (Easy), 180 (Medium), 240 (Hard).
- Final scores use Python `round(..., 1)` and are displayed to one decimal place.

For a Medium game with 90% average accuracy completed in 60 seconds:

```text
speed_bonus = 1.2 - 60 / 600 = 1.1
score       = 1.5 * 0.90 * 100 * 1.1 = 148.5
```

With the same accuracy at 120 seconds the score is 135.0; at 240 seconds or longer
it is 108.0. The accuracy average weights each scored attempt equally,
regardless of phrase length.

## Hard-only Swap and winning

There is no Skip action. Easy and Medium have no Swap; Hard offers **one Swap per
game**. Swap replaces the current challenge before submission without consuming a
round or recording an attempt. The game clock keeps running. The default UI runs
five scored rounds, including failed transcriptions in the accuracy average.

A completed game's `won` field is true when average accuracy >= 80%. Winning is
separate from the numeric leaderboard score: Hard and Medium apply larger score
multipliers, and a non-winning game still has a score. With no scored attempts,
average accuracy is zero.

Thresholds and multipliers are fixed in application code. The unused legacy
`game.winThreshold` setting has been removed; it never controlled the active 80%
threshold or meant "win four out of five". Remove it from older owner values files.
Change language membership through [difficulty groups](difficulty-groups.md),
not by editing score arithmetic.

### Historical database compatibility

Older versions could persist skipped attempts. Those records remain valid in
existing databases and backups and remain excluded from their scoring average.
Their elapsed time still counts. The API no longer accepts new skip submissions;
it does not rewrite old results or require a database reset/migration.

## Leaderboard

Only completed games appear. Each player appears once with their best score
across all difficulties; scores are not summed across games. Replaying can improve
that best score. TV, public leaderboard and best-score CSV use that result; the
all-games CSV also includes other completed games. There is no documented
secondary tie-break rule: tied scores are ordered by the current query, so agree
any prize tie procedure with the event owner beforehand.

The completion API calculates rank as one plus the number of players with a
strictly greater best score. The public leaderboard numbers the returned rows
sequentially; tied rows can therefore show different displayed rank numbers.

## Completion and retry behavior in the integration candidate

New games record their configured round count at creation and require all rounds
in order before completion. Identical attempt and completion retries return the
saved result. The UI keeps unconfirmed saves pending and exposes Retry save rather
than advancing or displaying success. Existing game rows retain historical scoring;
see [game mode and compatibility](game-mode.md). Standalone mode displays accuracy
and winning without persisting a tournament score.
