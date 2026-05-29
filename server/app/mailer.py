"""
Email sending for finger auth.

Configured via SMTP_* environment variables.

In development mode (SMTP_HOST not set), prints to server log.
"""

import logging
import os
import smtplib
from email.message import EmailMessage

logger = logging.getLogger("finger.mailer")


def _get_config() -> dict:
    return {
        "host": os.environ.get("SMTP_HOST", ""),
        "port": int(os.environ.get("SMTP_PORT", "587")),
        "user": os.environ.get("SMTP_USER", ""),
        "pass": os.environ.get("SMTP_PASS", ""),
        "from_addr": os.environ.get("FINGER_EMAIL_FROM", "finger@localhost"),
        "to_addr": os.environ.get("FINGER_USER_EMAIL", ""),
    }


def send_auth_email(token: str) -> bool:
    """Send the magic link email with the auth token.

    In dev mode (no SMTP_HOST), logs to stdout.
    Returns True if sent (or logged in dev mode).
    """
    cfg = _get_config()

    body = (
        f"You (or someone else) requested to authorize a finger client "
        f"for your account.\n\n"
        f"If this was you, run:\n\n"
        f"  finger --auth {token}\n\n"
        f"This code expires in 15 minutes.\n\n"
        f"If you did not request this, you can ignore this message."
    )

    if not cfg["host"]:
        # Dev mode — log instead of sending
        logger.info("--- AUTH EMAIL (dev mode) ---")
        logger.info("To: %s", cfg["to_addr"])
        logger.info("Token: %s", token)
        logger.info("---")
        return True

    msg = EmailMessage()
    msg.set_content(body)
    msg["Subject"] = "Finger authorization code"
    msg["From"] = cfg["from_addr"]
    msg["To"] = cfg["to_addr"]

    try:
        with smtplib.SMTP(cfg["host"], cfg["port"]) as smtp:
            if cfg["user"]:
                smtp.starttls()
                smtp.login(cfg["user"], cfg["pass"])
            smtp.send_message(msg)
        logger.info("Auth email sent to %s", cfg["to_addr"])
        return True
    except Exception as e:
        logger.error("Failed to send auth email: %s", e)
        return False
