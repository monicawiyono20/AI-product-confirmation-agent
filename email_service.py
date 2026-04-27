import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")


def send_confirmation_emails(agent_email: str, customer_email: str):
    agent_body = f"""Dear Agent,

This is to confirm that the customer ({customer_email}) has completed the AI product knowledge session.

The customer has confirmed that they understand the insurance product based on the original product specifications and agrees to proceed with payment.

You may now proceed with the payment process.

Best regards,
AI Insurance Assistant"""

    customer_body = f"""Dear Customer,

Thank you for completing the product knowledge session.

You have confirmed that you understand the insurance product you are purchasing. This email serves as a record that you were properly informed before proceeding with payment.

If you have any further questions, please contact your agent.

Best regards,
AI Insurance Assistant"""

    _send(agent_email, "Customer Confirmed Product Understanding - Proceed with Payment", agent_body)
    _send(customer_email, "Your Insurance Product Understanding Confirmation", customer_body)


def _send(to: str, subject: str, body: str):
    msg = MIMEMultipart()
    msg["From"] = SMTP_USER
    msg["To"] = to
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(SMTP_USER, to, msg.as_string())
