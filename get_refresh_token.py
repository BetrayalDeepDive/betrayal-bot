"""
Run this ONCE on your laptop to extract the YouTube refresh token.
Then add it as YOUTUBE_REFRESH_TOKEN secret in GitHub.

Run: python get_refresh_token.py
"""
import pickle, os

token_path = "C:\\BetrayalBot\\youtube_token.pkl"

try:
    creds = pickle.load(open(token_path, "rb"))
    print("\n" + "="*60)
    print("YOUR YOUTUBE REFRESH TOKEN:")
    print("="*60)
    print(creds.refresh_token)
    print("="*60)
    print("\nAdd this as YOUTUBE_REFRESH_TOKEN in GitHub Secrets:")
    print("https://github.com/BetrayalDeepDive/betrayal-bot/settings/secrets/actions")
    print("\nAlso confirm your Client ID and Secret match:")
    print(f"Client ID starts with: {creds.client_id[:30] if creds.client_id else 'NOT FOUND'}...")
except Exception as e:
    print(f"Error: {e}")
    print("Make sure youtube_token.pkl exists at C:\\BetrayalBot\\youtube_token.pkl")
