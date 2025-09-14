# Standard library imports
from datetime import UTC, datetime
from typing import Any

# Third-party imports
import httpx

# Local application imports
from app.settings import settings


async def send_mailgun_email(to_email: str, subject: str, text: str, html: str | None = None) -> None:
    """Sends an email using Mailgun asynchronously."""
    if settings.ENVIRONMENT == "dev":
        url = f"https://api.mailgun.net/v3/{settings.MAILGUN_DOMAIN}/messages"
    else:
        url = f"https://api.eu.mailgun.net/v3/{settings.MAILGUN_DOMAIN}/messages"
    auth = ("api", settings.MAILGUN_API_KEY)
    data = {
        "from": f"JanEye <noreply@{settings.MAILGUN_DOMAIN}>",
        "to": to_email,
        "subject": subject,
        "text": text,
    }
    if html:
        data["html"] = html

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, auth=auth, data=data)
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        print(f"HTTP Status Error: {exc.response.status_code}")
        print(f"Response body: {exc.response.text}")
        raise
    except Exception as e:
        print(f"Unexpected error in send_mailgun_email: {str(e)}")
        raise


async def send_bulk_mailgun_email(
    recipient_emails: list[str],
    subject: str,
    text: str,
    html: str | None = None,
    batch_size: int = 1000,
) -> tuple[int, int]:
    """
    Sends bulk email using Mailgun's batch sending feature.

    Args:
        recipient_emails: List of recipient email addresses
        subject: Email subject
        text: Plain text content
        html: Optional HTML content
        batch_size: Number of emails per batch (Mailgun limit is 1000)

    Returns:
        Tuple of (successful_count, failed_count)
    """
    if settings.ENVIRONMENT == "dev":
        url = f"https://api.mailgun.net/v3/{settings.MAILGUN_DOMAIN}/messages"
    else:
        url = f"https://api.eu.mailgun.net/v3/{settings.MAILGUN_DOMAIN}/messages"

    auth = ("api", settings.MAILGUN_API_KEY)
    successful = 0
    failed = 0

    # Split recipients into batches to respect Mailgun's limits
    for i in range(0, len(recipient_emails), batch_size):
        batch_emails = recipient_emails[i : i + batch_size]

        data = {
            "from": f"JanEye <noreply@{settings.MAILGUN_DOMAIN}>",
            "to": batch_emails,  # Mailgun accepts array of recipients
            "subject": subject,
            "text": text,
        }

        if html:
            data["html"] = html

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, auth=auth, data=data)
                response.raise_for_status()
                successful += len(batch_emails)
                print(f"Successfully sent batch of {len(batch_emails)} emails")

        except httpx.HTTPStatusError as exc:
            print(f"HTTP Status Error for batch: {exc.response.status_code}")
            print(f"Response body: {exc.response.text}")
            failed += len(batch_emails)
        except Exception as e:
            print(f"Unexpected error sending batch: {str(e)}")
            failed += len(batch_emails)

    return successful, failed


def load_registration_email_template(template_path: str, first_name: str, otp: str, logger: Any) -> str | None:
    try:
        with open(template_path, encoding="utf-8") as file:
            html_content = file.read()
        current_time = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
        html_content = (
            html_content.replace("{{ first_name }}", first_name)
            .replace("{{ current_time }}", current_time)
            .replace("{{ otp_code }}", otp)
        )
        logger.debug("Email template loaded and personalized successfully")
        return html_content
    except Exception as e:
        logger.error(f"Error loading email template: {str(e)}", exc_info=True)
        return None


def load_forget_password_email_template(template_path: str, link: str, logger: Any) -> str | None:
    try:
        with open(template_path, encoding="utf-8") as file:
            html_content = file.read()
        current_time = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
        html_content = html_content.replace("{{ current_time }}", current_time).replace("{{ link }}", link)
        logger.debug("Email template loaded and personalized successfully")
        return html_content
    except Exception as e:
        logger.error(f"Error loading email template: {str(e)}", exc_info=True)
        return None


def load_bulk_email_template(template_path: str, subject: str, content: str, category: str, logger: Any) -> str | None:
    """
    Load and personalize bulk email template.

    Args:
        template_path: Path to the HTML template file
        subject: Email subject line
        content: Email body content
        category: Email category (marketing, announcement, etc.)
        logger: Logger instance

    Returns:
        Personalized HTML content or None if error
    """
    try:
        with open(template_path, encoding="utf-8") as file:
            html_content = file.read()

        current_time = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")

        # Format content for HTML (convert line breaks)
        formatted_content = content.replace(chr(10), "<br>").replace(chr(13), "")

        # Format category for display
        formatted_category = category.replace("_", " ").title()

        # Detect CTA and create button
        cta_words = [
            "visit",
            "click",
            "learn more",
            "get started",
            "sign up",
            "login",
            "explore",
        ]
        has_cta = any(word in content.lower() for word in cta_words)

        cta_button = ""
        if has_cta:
            cta_button = """
            <div style="text-align: center; margin: 40px 0;">
              <a href="https://janeye.in" style="
                    display: inline-block;
                    padding: 15px 30px;
                    background-color: #499fb6;
                    color: #ffffff;
                    text-decoration: none;
                    font-size: 16px;
                    font-weight: 600;
                    border-radius: 8px;
                  " target="_blank">Visit JanEye</a>
            </div>
            """

        # Replace template variables
        html_content = (
            html_content.replace("{{ subject }}", subject)
            .replace("{{ content }}", formatted_content)
            .replace("{{ category }}", formatted_category)
            .replace("{{ current_time }}", current_time)
            .replace("{{ cta_button }}", cta_button)
        )

        logger.debug("Bulk email template loaded and personalized successfully")
        return html_content

    except Exception as e:
        logger.error(f"Error loading bulk email template: {str(e)}", exc_info=True)
        return None
