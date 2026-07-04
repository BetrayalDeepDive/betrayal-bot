# ============================================================
# BETRAYAL DEEPDIVE — Weekly Self-Improvement Report
# Runs: Sunday 3:30 AM UTC = 9:00 AM IST
# Pulls your own analytics + competitor channels, analyses retention
# drop-off by script stage, recalibrates the title model, and writes
# next_week_strategy.json (read by Monday's script generation) — then
# sends the full report to Telegram.
#
# THIS WORKFLOW DID NOT EXIST BEFORE — weekly_report.py has been sitting
# in the repo this whole time with no scheduled trigger, which is very
# likely the entire reason no weekly report has ever arrived in Telegram.
# ============================================================
name: Weekly Self-Improvement Report

on:
  schedule:
    - cron: '30 3 * * 0'   # 9:00 AM IST | Sunday
  workflow_dispatch:

env:
  PYTHONUNBUFFERED: "1"

jobs:
  weekly-report:
    runs-on: ubuntu-latest
    timeout-minutes: 60
    permissions:
      contents: write

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install requests -q

      - name: Pull latest state
        run: |
          git config user.email "action@github.com"
          git config user.name "GitHub Actions"
          git pull --rebase origin main || true

      - name: Run weekly report
        env:
          GEMINI_API_KEY:        ${{ secrets.GEMINI_API_KEY }}
          GROQ_API_KEY:          ${{ secrets.GROQ_API_KEY }}
          CEREBRAS_API_KEY:      ${{ secrets.CEREBRAS_API_KEY }}
          YOUTUBE_CLIENT_ID:     ${{ secrets.YOUTUBE_CLIENT_ID }}
          YOUTUBE_CLIENT_SECRET: ${{ secrets.YOUTUBE_CLIENT_SECRET }}
          YOUTUBE_REFRESH_TOKEN: ${{ secrets.YOUTUBE_REFRESH_TOKEN }}
          TELEGRAM_TOKEN:        ${{ secrets.TELEGRAM_TOKEN }}
          TELEGRAM_CHAT_ID:      ${{ secrets.TELEGRAM_CHAT_ID }}
        run: |
          python -u video_pipeline/weekly_report.py

      - name: Commit strategy file
        if: always()
        run: |
          git config user.email "action@github.com"
          git config user.name "GitHub Actions"
          git add video_pipeline/next_week_strategy.json || true
          git diff --staged --quiet || git commit -m "chore: weekly report [skip ci]"
          # Retry push instead of silently dropping it on conflict — this
          # exact "|| true" silent-failure pattern is what broke Ch1's
          # uploads for two weeks earlier in this project.
          for i in 1 2 3 4 5; do
            if git push origin main; then
              echo "Push succeeded on attempt $i"
              break
            fi
            echo "Push failed (attempt $i) — pulling + retrying in $((i*5))s"
            sleep $((i*5))
            git pull --rebase origin main || true
            if [ "$i" = "5" ]; then
              echo "::error::Push failed after 5 attempts — commit did NOT reach GitHub"
            fi
          done
