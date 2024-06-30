from __future__ import annotations

import json
import os.path
import time
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

MESSAGE_LIST_FILE = "message_list.json"
POLITENESS_SLEEP = 2


def authenticate() -> Credentials:
    """
    Authenticate against the google OAuth server.

    Requires: `credentials.json` to exist

    This will create a token.json file when successful. A local browser must
    be discoverable to succeed.
    """
    creds = None

    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    if not creds:
        raise ValueError("Invalid creds")

    return creds


def build_message_list(creds: Credentials) -> None:
    """
    Builds a `message_list.json` file which contains data for all messages.

    Note: Delete the `message_list.json` file to force a full refresh of all messges.

    JSON Format:
        {
            "messageId": {
                "From": [str],
                "Title": [str],
                "Timestamp": [int]
            }
        }

    Args:
        creds: Authentication Credentials
    """
    seen_ids: set[str] = set()
    message_json: dict[str, Any] = {}

    if os.path.exists(MESSAGE_LIST_FILE):
        print("Loading existing ids from file...")
        with open(MESSAGE_LIST_FILE, "r", encoding="utf-8") as infile:
            message_json = json.load(infile)
        seen_ids = set(message_json.keys())

    service = build("gmail", "v1", credentials=creds)

    next_page_token = ""
    while "The Wild Things dance":
        print(f"Fetching message ids. {len(message_json)} found so far...")
        results = (
            service.users()
            .messages()
            .list(
                userId="me",
                maxResults=500,
                pageToken=next_page_token,
            )
            .execute()
        )
        next_page_token = results.get("nextPageToken", "")

        new_ids: set[str] = {message["id"] for message in results.get("messages", [])}

        if not new_ids.difference(seen_ids):
            print("All ids accounted for, assuming we have all ids and stopping.")
            break

        seen_ids |= new_ids

        for message in results.get("messages"):
            message_json[message["id"]] = {"From": "", "Title": "", "Timestamp": 0}

        with open(MESSAGE_LIST_FILE, "w", encoding="utf-8") as outfile:
            json.dump(message_json, outfile)

        if not next_page_token:
            print("All ids captured")
            break

        time.sleep(POLITENESS_SLEEP)


def main() -> int:
    """Main entry point."""
    creds = authenticate()
    build_message_list(creds)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
