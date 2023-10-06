from fastapi import HTTPException
from fastapi.responses import JSONResponse
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
import os

from pydantic import EmailStr, BaseModel


class EmailSchema(BaseModel):
    email: EmailStr


conf = ConnectionConfig(
    MAIL_USERNAME=os.getenv("SMTP_USERNAME"),
    MAIL_PASSWORD=os.getenv("SMTP_PASSWORD"),
    MAIL_FROM="homework122@meta.ua",
    MAIL_PORT=os.getenv("SMTP_PORT"),
    MAIL_SERVER=os.getenv("SMTP_SERVER"),
    MAIL_STARTTLS=False,
    MAIL_SSL_TLS=True,
)

fast_mail = FastMail(conf)


async def send_email_verification(email: str, verification_token: str):
    message = MessageSchema(
        subject="Підтвердження електронної пошти",
        recipients=[email],
        body=f"Перейдіть за посиланням для підтвердження: http://example.com/confirm-email?token={verification_token}",
        subtype=MessageType.html,
    )

    try:
        await fast_mail.send_message(message)
        return JSONResponse(content={"message": "Email sent successfully"})
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Помилка відправки листа: {str(e)}"
        )
