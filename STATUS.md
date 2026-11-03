# STATUS

## Placeholders you need to fill
(filled in at the end of the run)

## Done
- Phase 0: venv (Python 3.11), requirements, repo layout, git. `gh` already authenticated as jkknikhil-git.
- Phase 1: FLORES-200 devtest from the official tarball (1,012 sentences x 12 languages).
  Training corpus: 50,000 train + 100 held-out sentences per language from `ai4bharat/sangraha` (verified split,
  first two parquet shards, streamed). 0 sentences overlapped FLORES dev+devtest. See `results/corpus_stats.json`.

## Skipped / failed
- `ai4bharat/IN22-Gen` is gated (`gated=auto`, needs a login) -> skipped as instructed; FLORES-200 is the only benchmark.

## Next
- Phase 2-3 metrics over the tokenizer zoo.
