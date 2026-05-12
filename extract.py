import pandas as pd
import pyarrow.parquet as pq
import os
import re
import gc
import sys
import time
import json
import argparse
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- Configuration ---
INPUT_PARQUET   = 'rdns-march.parquet'
INPUT_CSV       = 'countries.csv'
OUTPUT_DIR      = './outputs'
CHECKPOINT_FILE = './outputs/.checkpoint.json'
BATCH_SIZE      = 100_000   # Lower than 200k for WSL stability
MAX_WORKERS     = 2         # Threads for parallel country matching per batch

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# 0. Argument parsing
# ---------------------------------------------------------------------------
parser = argparse.ArgumentParser(description='Extract domains from parquet using country CSV.')
parser.add_argument('--restart', action='store_true',
                    help='Resume from the last saved checkpoint batch')
parser.add_argument('--batch', type=int, metavar='N',
                    help='Resume from a specific batch number (skips batches 0..N-1)')
args = parser.parse_args()

if args.restart and args.batch is not None:
    print("Error: use either --restart or --batch N, not both.")
    sys.exit(1)

def save_checkpoint(batch_index: int, total_matches: int) -> None:
    with open(CHECKPOINT_FILE, 'w') as f:
        json.dump({'last_batch': batch_index, 'total_matches': total_matches}, f)

def load_checkpoint() -> tuple[int, int]:
    try:
        with open(CHECKPOINT_FILE) as f:
            data = json.load(f)
            return data['last_batch'], data['total_matches']
    except (FileNotFoundError, KeyError):
        return -1, 0

if args.restart:
    resume_from, total_matches_loaded = load_checkpoint()
    if resume_from >= 0:
        print(f"Resuming from batch {resume_from + 1} ({total_matches_loaded:,} matches so far).")
    else:
        print("No checkpoint found — starting from the beginning.")
        total_matches_loaded = 0
elif args.batch is not None:
    resume_from = args.batch - 1
    total_matches_loaded = 0
    print(f"Jumping to batch {args.batch} (matches before this point not counted).")
else:
    resume_from, total_matches_loaded = -1, 0
    if os.path.exists(CHECKPOINT_FILE):
        os.remove(CHECKPOINT_FILE)

# ---------------------------------------------------------------------------
# 1. Load country search map and pre-compile regex patterns
# ---------------------------------------------------------------------------
try:
    df_search = pd.read_csv(INPUT_CSV)
    if 'government domain' not in df_search.columns:
        df_search = pd.read_csv(INPUT_CSV, sep='\t')

    # Build {code: [domain, ...]} map
    search_map: dict[str, list[str]] = (
        df_search
        .groupby('code')['government domain']
        .apply(lambda x: [str(d).strip().lower() for d in x if str(d).strip()])
        .to_dict()
    )

    # Pre-compile one regex per country — matches exact root OR any subdomain
    # Pattern: (^|\.)root1$|(^|\.)root2$  ...
    def build_pattern(roots: list[str]) -> re.Pattern:
        escaped = [re.escape(r) for r in roots]
        alts = '|'.join(rf'(?:^|\.){e}$' for e in escaped)
        return re.compile(alts)

    pattern_map: dict[str, re.Pattern] = {
        code: build_pattern(roots)
        for code, roots in search_map.items()
        if roots
    }

    print(f"Loaded {len(search_map)} country profiles with compiled patterns.")
except Exception as e:
    print(f"Critical Error loading CSV: {e}")
    sys.exit(1)

# ---------------------------------------------------------------------------
# 2. Per-batch processing helpers
# ---------------------------------------------------------------------------

def match_country(args):
    """Match one country's pattern against the domain Series. Returns (code, matches)."""
    code, pattern, domains_lower = args
    mask = domains_lower.str.contains(pattern, regex=True, na=False)
    matches = domains_lower[mask].unique().tolist()
    return code, matches


def process_batch(df_slice: pd.DataFrame) -> dict[str, set[str]]:
    """Return {code: set_of_matched_domains} for a single batch."""
    # Lowercase once for the whole batch — avoids repeated lowercasing per country
    domains_lower = df_slice['domain'].str.lower().str.strip()

    results: dict[str, set[str]] = defaultdict(set)

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(match_country, (code, pat, domains_lower)): code
            for code, pat in pattern_map.items()
        }
        for future in as_completed(futures):
            code, matches = future.result()
            if matches:
                results[code].update(matches)

    return results


def flush_results(batch_results: dict[str, set[str]]) -> None:
    """Append matched domains to per-country output files."""
    for code, domains in batch_results.items():
        if not domains:
            continue
        output_path = os.path.join(OUTPUT_DIR, f"{str(code).lower()}.txt")
        with open(output_path, 'a', encoding='utf-8') as f:
            f.write('\n'.join(sorted(domains)) + '\n')

# ---------------------------------------------------------------------------
# 3. Main loop — stream Parquet in batches
# ---------------------------------------------------------------------------
try:
    parquet_file = pq.ParquetFile(INPUT_PARQUET)
    total_batches = 0
    total_matches = total_matches_loaded
    t_start = time.time()

    for i, batch in enumerate(parquet_file.iter_batches(batch_size=BATCH_SIZE)):

        # Skip already-processed batches when resuming
        if i <= resume_from:
            del batch
            if i % 500 == 0:
                print(f"Skipping batch {i} (already processed)...")
            continue

        t_batch = time.time()

        df_slice = batch.to_pandas()
        batch_results = process_batch(df_slice)

        match_count = sum(len(v) for v in batch_results.values())
        total_matches += match_count

        flush_results(batch_results)

        # Save checkpoint after every batch
        save_checkpoint(i, total_matches)

        # Explicit cleanup — important for WSL which doesn't aggressively reclaim RAM
        del df_slice, batch_results, batch
        gc.collect()

        elapsed = time.time() - t_batch
        print(
            f"Batch {i:4d} | "
            f"{BATCH_SIZE:,} rows | "
            f"{match_count:,} new matches | "
            f"{total_matches:,} total | "
            f"{elapsed:.1f}s"
        )
        total_batches += 1

    elapsed_total = time.time() - t_start
    print(
        f"\nDone. {total_batches} batches, {total_matches:,} total matches "
        f"in {elapsed_total:.1f}s → ./outputs/"
    )
    # Clear checkpoint on clean completion
    if os.path.exists(CHECKPOINT_FILE):
        os.remove(CHECKPOINT_FILE)

except KeyboardInterrupt:
    print("\nInterrupted — partial results saved to ./outputs/")
    sys.exit(0)
except FileNotFoundError:
    print(f"Error: '{INPUT_PARQUET}' not found.")
    sys.exit(1)
except Exception as e:
    print(f"Unexpected error: {e}")
    raise