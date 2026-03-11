"""Gmail tool using the Google Gmail API with OAuth2.

Provides email listing, searching, reading, sending, drafting, and management.
Requires OAuth2 credentials (credentials.json from Google Cloud Console).
"""

import asyncio
import base64
import json
import os
from email.mime.text import MIMEText
from pathlib import Path
from typing import ClassVar, Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field, PrivateAttr

from agent.logger import get_logger

logger = get_logger("agent.tools.gmail", component="gmail")

# Token and credentials file paths
CREDENTIALS_FILE = os.getenv("GMAIL_CREDENTIALS_FILE", "credentials.json")
TOKEN_FILE = os.getenv("GMAIL_TOKEN_FILE", "gmail_token.json")
SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]


# =============================================================================
# Input Schema
# =============================================================================


class GmailInput(BaseModel):
    action: str = Field(
        ...,
        description=(
            "Action to perform: "
            "'list' — list recent emails from inbox, "
            "'search' — search emails with Gmail query syntax, "
            "'read' — read a specific email by ID, "
            "'send' — send an email, "
            "'draft' — create a draft email, "
            "'mark_read' — mark an email as read, "
            "'delete' — move an email to trash, "
            "'profile' — get email account profile info."
        ),
    )
    message_id: str = Field(default="", description="Email message ID for 'read', 'mark_read', 'delete'.")
    query: str = Field(
        default="",
        description=(
            "Gmail search query for 'search'. Examples: "
            "'from:user@example.com', 'subject:invoice', 'is:unread', "
            "'newer_than:1d', 'has:attachment'."
        ),
    )
    to: str = Field(default="", description="Recipient email address for 'send' or 'draft'.")
    subject: str = Field(default="", description="Email subject for 'send' or 'draft'.")
    body: str = Field(default="", description="Email body text for 'send' or 'draft'.")
    max_results: int = Field(default=10, ge=1, le=50, description="Max emails to return (default: 10).")


# =============================================================================
# Tool Implementation
# =============================================================================


class GmailTool(BaseTool):
    name: str = "gmail"
    description: str = (
        "Manage Gmail: list, search, read, send, draft, and organize emails. "
        "Requires Google OAuth2 setup (credentials.json from Google Cloud Console).\n\n"
        "Examples:\n"
        "- List inbox: action='list', max_results=10\n"
        "- Search: action='search', query='from:boss@company.com is:unread'\n"
        "- Read email: action='read', message_id='18abc123'\n"
        "- Send email: action='send', to='user@example.com', subject='Hello', body='Hi there!'\n"
        "- Create draft: action='draft', to='user@example.com', subject='Draft', body='...'\n"
        "- Mark as read: action='mark_read', message_id='18abc123'\n"
        "- Delete: action='delete', message_id='18abc123'\n"
        "- Profile: action='profile'"
    )
    args_schema: Type[BaseModel] = GmailInput
    handle_tool_error: bool = True

    _service: Optional[object] = PrivateAttr(default=None)

    MAX_CONTENT_CHARS: ClassVar[int] = 3000

    def _get_service(self):
        """Get or create the Gmail API service with OAuth2 auth."""
        if self._service is not None:
            return self._service

        try:
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build
        except ImportError:
            raise RuntimeError(
                "Gmail requires google packages. Install with: "
                "pip install google-auth google-auth-oauthlib google-api-python-client"
            )

        creds = None
        token_path = Path(TOKEN_FILE)

        # Load existing token
        if token_path.exists():
            creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

        # Refresh or create new credentials
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                creds_path = Path(CREDENTIALS_FILE)
                if not creds_path.exists():
                    raise RuntimeError(
                        f"Gmail credentials file '{CREDENTIALS_FILE}' not found. "
                        "Download it from Google Cloud Console > APIs & Services > Credentials."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), SCOPES)
                creds = flow.run_local_server(port=0)

            # Save token for future use
            token_path.write_text(creds.to_json())
            logger.info("gmail_token_saved", path=str(token_path))

        self._service = build("gmail", "v1", credentials=creds)
        return self._service

    def _extract_headers(self, headers: list, *names: str) -> dict:
        """Extract specific headers from a message."""
        result = {}
        name_set = {n.lower() for n in names}
        for h in headers:
            if h["name"].lower() in name_set:
                result[h["name"].lower()] = h["value"]
        return result

    def _format_message_summary(self, msg: dict) -> dict:
        """Format a message into a compact summary."""
        headers = msg.get("payload", {}).get("headers", [])
        extracted = self._extract_headers(headers, "From", "To", "Subject", "Date")
        labels = msg.get("labelIds", [])

        return {
            "id": msg["id"],
            "from": extracted.get("from", ""),
            "to": extracted.get("to", ""),
            "subject": extracted.get("subject", ""),
            "date": extracted.get("date", ""),
            "snippet": msg.get("snippet", ""),
            "unread": "UNREAD" in labels,
        }

    def _get_message_body(self, payload: dict) -> str:
        """Extract plain text body from message payload."""
        if payload.get("mimeType") == "text/plain" and payload.get("body", {}).get("data"):
            return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")

        # Check parts recursively
        for part in payload.get("parts", []):
            if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
                return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
            # Nested multipart
            body = self._get_message_body(part)
            if body:
                return body

        return ""

    def _list_messages(self, max_results: int) -> str:
        service = self._get_service()
        results = service.users().messages().list(
            userId="me", maxResults=max_results, labelIds=["INBOX"]
        ).execute()

        messages = results.get("messages", [])
        if not messages:
            return json.dumps({"count": 0, "messages": [], "hint": "Inbox is empty."})

        summaries = []
        for msg_ref in messages:
            msg = service.users().messages().get(
                userId="me", id=msg_ref["id"], format="metadata",
                metadataHeaders=["From", "To", "Subject", "Date"],
            ).execute()
            summaries.append(self._format_message_summary(msg))

        return json.dumps({"count": len(summaries), "messages": summaries}, indent=2)

    def _search_messages(self, query: str, max_results: int) -> str:
        if not query:
            return json.dumps({"error": "Provide a search query (e.g., query='is:unread')"})

        service = self._get_service()
        results = service.users().messages().list(
            userId="me", q=query, maxResults=max_results
        ).execute()

        messages = results.get("messages", [])
        if not messages:
            return json.dumps({"query": query, "count": 0, "messages": []})

        summaries = []
        for msg_ref in messages:
            msg = service.users().messages().get(
                userId="me", id=msg_ref["id"], format="metadata",
                metadataHeaders=["From", "To", "Subject", "Date"],
            ).execute()
            summaries.append(self._format_message_summary(msg))

        return json.dumps({"query": query, "count": len(summaries), "messages": summaries}, indent=2)

    def _read_message(self, message_id: str) -> str:
        if not message_id:
            return json.dumps({"error": "Provide a message_id"})

        service = self._get_service()
        msg = service.users().messages().get(
            userId="me", id=message_id, format="full"
        ).execute()

        headers = msg.get("payload", {}).get("headers", [])
        extracted = self._extract_headers(headers, "From", "To", "Subject", "Date", "Cc")
        body = self._get_message_body(msg.get("payload", {}))

        # Get attachments info
        attachments = []
        for part in msg.get("payload", {}).get("parts", []):
            if part.get("filename"):
                attachments.append({
                    "filename": part["filename"],
                    "mimeType": part.get("mimeType"),
                    "size": part.get("body", {}).get("size", 0),
                })

        return json.dumps({
            "id": msg["id"],
            "thread_id": msg.get("threadId"),
            "from": extracted.get("from", ""),
            "to": extracted.get("to", ""),
            "cc": extracted.get("cc", ""),
            "subject": extracted.get("subject", ""),
            "date": extracted.get("date", ""),
            "body": body[:self.MAX_CONTENT_CHARS],
            "labels": msg.get("labelIds", []),
            "attachments": attachments,
        }, indent=2)

    def _send_message(self, to: str, subject: str, body: str) -> str:
        if not to or not subject:
            return json.dumps({"error": "Provide 'to' and 'subject'"})

        service = self._get_service()
        message = MIMEText(body)
        message["to"] = to
        message["subject"] = subject

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        result = service.users().messages().send(
            userId="me", body={"raw": raw}
        ).execute()

        return json.dumps({
            "sent": True,
            "id": result.get("id"),
            "thread_id": result.get("threadId"),
            "to": to,
            "subject": subject,
        }, indent=2)

    def _create_draft(self, to: str, subject: str, body: str) -> str:
        if not to or not subject:
            return json.dumps({"error": "Provide 'to' and 'subject'"})

        service = self._get_service()
        message = MIMEText(body)
        message["to"] = to
        message["subject"] = subject

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        result = service.users().drafts().create(
            userId="me", body={"message": {"raw": raw}}
        ).execute()

        return json.dumps({
            "drafted": True,
            "draft_id": result.get("id"),
            "to": to,
            "subject": subject,
        }, indent=2)

    def _mark_read(self, message_id: str) -> str:
        if not message_id:
            return json.dumps({"error": "Provide a message_id"})

        service = self._get_service()
        service.users().messages().modify(
            userId="me", id=message_id,
            body={"removeLabelIds": ["UNREAD"]},
        ).execute()

        return json.dumps({"marked_read": True, "id": message_id})

    def _delete_message(self, message_id: str) -> str:
        if not message_id:
            return json.dumps({"error": "Provide a message_id"})

        service = self._get_service()
        service.users().messages().trash(userId="me", id=message_id).execute()

        return json.dumps({"trashed": True, "id": message_id})

    def _get_profile(self) -> str:
        service = self._get_service()
        profile = service.users().getProfile(userId="me").execute()

        return json.dumps({
            "email": profile.get("emailAddress"),
            "messages_total": profile.get("messagesTotal"),
            "threads_total": profile.get("threadsTotal"),
            "history_id": profile.get("historyId"),
        }, indent=2)

    # -------------------------------------------------------------------------
    # BaseTool interface
    # -------------------------------------------------------------------------

    def _run(
        self,
        action: str,
        message_id: str = "",
        query: str = "",
        to: str = "",
        subject: str = "",
        body: str = "",
        max_results: int = 10,
    ) -> str:
        logger.info("gmail_action", action=action)
        try:
            match action.lower():
                case "list":
                    return self._list_messages(max_results)
                case "search":
                    return self._search_messages(query, max_results)
                case "read":
                    return self._read_message(message_id)
                case "send":
                    return self._send_message(to, subject, body)
                case "draft":
                    return self._create_draft(to, subject, body)
                case "mark_read":
                    return self._mark_read(message_id)
                case "delete":
                    return self._delete_message(message_id)
                case "profile":
                    return self._get_profile()
                case _:
                    return json.dumps({
                        "error": f"Unknown action '{action}'. "
                        "Use: list, search, read, send, draft, mark_read, delete, profile"
                    })
        except Exception as e:
            logger.error("gmail_error", error=str(e))
            return json.dumps({"error": str(e)})

    async def _arun(
        self,
        action: str,
        message_id: str = "",
        query: str = "",
        to: str = "",
        subject: str = "",
        body: str = "",
        max_results: int = 10,
    ) -> str:
        return await asyncio.to_thread(
            self._run, action, message_id, query, to, subject, body, max_results
        )
