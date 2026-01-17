# Test Scripts Guide

This directory contains scripts for testing and scoring student-topic pairs.

## Available Scripts

### 1. `test_and_submit.py` (Recommended - All-in-One)

Complete workflow that scores all student-topic pairs and submits predictions in one command.

**Usage:**
```bash
# Run scoring and submit for dev_mini dataset (default)
python scripts/test_and_submit.py

# Run for a different dataset
python scripts/test_and_submit.py --dataset=dev

# Run without submitting (just score and save)
python scripts/test_and_submit.py --submit=False

# Custom output file and workers
python scripts/test_and_submit.py --dataset=dev --max_workers=4 --output=my_results.json

# Run without saving results file
python scripts/test_and_submit.py --save_results=False
```

**What it does:**
1. Fetches all students from the specified dataset
2. Runs tutoring sessions for each student (all topics per student)
3. Scores each student-topic pair (1-5 scale)
4. Saves results to JSON file
5. Submits predictions to the API (if `--submit=True`)

---

### 2. `test_tutor_orchestrator.py` (Score Only)

Scores all student-topic pairs and saves to JSON (no submission).

**Usage:**
```bash
# Score dev_mini dataset
python scripts/test_tutor_orchestrator.py

# Score different dataset
python scripts/test_tutor_orchestrator.py --dataset=dev --output=dev_results.json

# Use more workers
python scripts/test_tutor_orchestrator.py --max_workers=8
```

**What it does:**
1. Fetches all students from dataset
2. Runs tutoring sessions in parallel
3. Saves results to JSON file
4. **Does NOT submit** predictions

---

### 3. `submit_predictions.py` (Submit Only)

Submits predictions from a JSON file to the API.

**Usage:**
```bash
# Submit predictions from default file (out.json)
python scripts/submit_predictions.py

# Submit from custom file
python scripts/submit_predictions.py --input_file=results_dev_20260117.json --dataset=dev

# Dry run (see what would be submitted without actually submitting)
python scripts/submit_predictions.py --input_file=out.json --dry_run=True
```

**What it does:**
1. Reads JSON file with test results
2. Submits each prediction to the API
3. Shows progress and success/failure counts

---

### 4. `test_student.py` (Simple Test)

Simple script to test a single student-topic interaction.

**Usage:**
```bash
python scripts/test_student.py
```

---

## Typical Workflows

### Workflow A: All-in-One (Recommended)
```bash
# Run everything in one command
python scripts/test_and_submit.py --dataset=dev_mini
```

### Workflow B: Separate Steps
```bash
# Step 1: Score all students
python scripts/test_tutor_orchestrator.py --dataset=dev_mini --output=results.json

# Step 2: Review results (optional)
cat results.json

# Step 3: Submit predictions
python scripts/submit_predictions.py --input_file=results.json --dataset=dev_mini
```

### Workflow C: Score Now, Submit Later
```bash
# Score and save (don't submit yet)
python scripts/test_and_submit.py --dataset=dev --submit=False --output=dev_results.json

# Review or modify results...

# Submit when ready
python scripts/submit_predictions.py --input_file=dev_results.json --dataset=dev
```

---

## Output Format

All scoring scripts produce JSON output in this format:

```json
{
  "results": {
    "student_id_1": [
      {
        "student_id": "...",
        "topic_id": "...",
        "score": 3
      },
      {
        "student_id": "...",
        "topic_id": "...",
        "score": 4
      }
    ],
    "student_id_2": [...]
  },
  "errors": {
    "student_id_3": "Error message..."
  }
}
```

### Score Levels
- `1` - STRUGGLING
- `2` - BELOW_GRADE
- `3` - AT_GRADE
- `4` - ABOVE_GRADE
- `5` - ADVANCED

---

## Environment Variables

Make sure these are set in your `.env` file:

```bash
KNOWUNITY_API_KEY=your_api_key
KNOWUNITY_API_URL=https://knowunity-agent-olympics-2026-api.vercel.app
OPENAI_API_KEY=your_openai_key
LLM_API_URL=your_llm_url
MODEL_NAME=your_model_name
```

---

## Performance Tips

1. **Parallel Processing**: Use `--max_workers` to control parallelism
   - Default: CPU count
   - More workers = faster but more memory usage
   - Example: `--max_workers=4`

2. **Dataset Selection**:
   - `mini_dev` - Small dataset for quick testing
   - `dev` - Full development dataset
   - Custom datasets as needed

3. **Monitoring Progress**:
   - All scripts show real-time progress
   - Check output file during execution to see partial results

---

## Troubleshooting

### Issue: "No results found in input file"
- Make sure you ran the scoring script first
- Check that the input file path is correct

### Issue: API submission failures
- Verify `KNOWUNITY_API_KEY` is set correctly
- Check network connection
- Review API rate limits

### Issue: Scoring fails for some students
- Check the `errors` section in the output JSON
- Review logs for specific error messages
- Some students may have invalid data

---

## Examples

```bash
# Quick test on mini dataset
python scripts/test_and_submit.py

# Full production run on dev dataset with 8 workers
python scripts/test_and_submit.py --dataset=dev --max_workers=8

# Score only, review manually, then submit
python scripts/test_tutor_orchestrator.py --dataset=dev --output=dev_scored.json
python scripts/submit_predictions.py --input_file=dev_scored.json --dataset=dev

# Dry run to see what would be submitted
python scripts/submit_predictions.py --input_file=results.json --dry_run=True
```
