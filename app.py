from dotenv import load_dotenv
import os
import africastalking
from fastapi import FastAPI
from fastapi.requests import Request
from fastapi.responses import JSONResponse

from models.models import SessionConfig
from agent.ai_agent import process_sms_message
from SMS.sms import send_message

app = FastAPI()

load_dotenv()

africastalking.initialize(
    username="sandbox",
    api_key=os.getenv("AT_SANDBOX_API_KEY"),
)

sms = africastalking.SMS

config = SessionConfig(
        max_messages_per_session=30,  # Lower for testing
        session_duration_hours=1,
        max_sessions_per_day=10
    )


@app.post("/receive-sms")
async def sms_callback(request: Request):
    """
    Endpoint to receive SMS callbacks from Africa's Talking.
    """
    content_type = request.headers.get("content-type")
    print("Content-Type:", content_type)

    if "application/x-www-form-urlencoded" in content_type:
        form_data = await request.form()
        payload = dict(form_data)
        user_phone = payload.get("from")
        user_message = payload.get("text", "")
        response = process_sms_message(user_phone, user_message, config)
        send_message(
            recipients=[user_phone],
            message=response
        )
    else:
        payload = {"error": "Unsupported content type"}

    print("Received callback:", payload)
    return {"status": "received"}
