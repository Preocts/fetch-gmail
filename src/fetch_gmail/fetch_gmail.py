from __future__ import annotations

import os.path
import time

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow  # type: ignore
from googleapiclient.discovery import build  # type: ignore

from .messagestore import MessageStore

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


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


def build_message_list(
    creds: Credentials,
    store: MessageStore,
    *,
    delay: float = 0.25,
) -> None:
    """
    Builds a `message_list.json` file which contains data for all messages.

    Note: Delete the `message_list.json` file to force a full refresh of all messges.

    Args:
        creds: Authentication Credentials
        store: MessageStore object
        delay: Number of seconds to pause between request
    """
    service = build("gmail", "v1", credentials=creds)

    next_page_token = ""
    while "The Wild Things dance":
        print(f"Fetching message ids. {store.row_count()} found so far...")
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

        if not store.has_unique_ids(new_ids):
            print("All ids accounted for, assuming we have all ids and stopping.")
            break

        store.save_message_ids(new_ids)

        if not next_page_token:
            print("All ids captured")
            break

        time.sleep(delay)


def hydrate_message_list(
    creds: Credentials,
    store: MessageStore,
    *,
    delay: float = 0.25,
) -> None:
    """
    Get details of any message id that has not already been fetched.

    Args:
        creds: Authentication Credentials
        store: MessageStore object
        delay: Number of seconds to pause between request
    """
    service = build("gmail", "v1", credentials=creds)

    to_fetch = store.row_count(only_empty=True)
    for idx, messageid in enumerate(store.get_emtpy_message_ids(), start=1):
        print(f"Hydrating message {idx} of {to_fetch}.")

        results = (
            service.users()
            .messages()
            .get(
                userId="me",
                id=messageid,
                format="metadata",
                metadataHeaders=["From", "Subject", "Delivered-To"],
            )
            .execute()
        )

        message_data = {"Timestamp": results["internalDate"]}
        for header in results["payload"]["headers"]:
            if header["name"] == "From":
                message_data["From"] = header["value"]

            if header["name"] == "Subject":
                message_data["Subject"] = header["value"]

            if header["name"] == "Delivered-To":
                message_data["Delivered-To"] = header["value"]

        store.update(
            message_id=messageid,
            from_=message_data.get("From", ""),
            delivered_to=message_data.get("Delivered-To", ""),
            subject=message_data.get("Subject", ""),
            timestamp=message_data.get("Timestamp", "0"),
        )

        time.sleep(delay)


def main() -> int:
    """Main entry point."""
    store = MessageStore()
    store.init_file()
    creds = authenticate()
    build_message_list(creds, store)
    hydrate_message_list(creds, store)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
