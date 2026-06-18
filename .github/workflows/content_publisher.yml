name: DeepDive Content Publisher

on:
  schedule:
    - cron: '30 2 * * *'   # 8:00 AM IST daily
  workflow_dispatch:

jobs:
  publish_content:
    runs-on: ubuntu-latest
    timeout-minutes: 15

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install groq requests --break-system-packages -q

      - name: Run Content Publisher
        env:
          PYTHONUNBUFFERED: "1"
          GEMINI_API_KEY:   ${{ secrets.GEMINI_API_KEY }}
          GROQ_API_KEY:     ${{ secrets.GROQ_API_KEY }}
          DEVTO_API_KEY:    ${{ secrets.DEVTO_API_KEY }}
          TELEGRAM_TOKEN:   ${{ secrets.TELEGRAM_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
        run: python -u content_publisher.py

      - name: Upload Medium article as artifact
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: medium-article-${{ github.run_number }}
          path: medium_article_*.md
          retention-days: 30
