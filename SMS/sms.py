from dotenv import load_dotenv
import os
import africastalking
from typing import List

load_dotenv()

# Initialize the SDK
africastalking.initialize(
    username="sandbox",
    api_key=os.getenv("AT_SANDBOX_API_KEY"),
)

sms = africastalking.SMS

def send_message(recipients: List = ["+254720705104"], message: str = "Hello from Africa's Talking!"):
    """
    Function to send SMS using Africa's Talking API.
    This can be used to send messages to any recipient(s) using the Africa's Talking SMS service.
    """
    # Set your shortCode or senderId
    sender = os.getenv("AT_SHORT_CODE")
    
    try:
        response = sms.send(
                message=message,
                recipients=recipients,  # replace with your recipient's phone number
                sender_id=sender # your Alphanumeric sender ID
            )

        print(response)
        return response
    except Exception as e:
        raise f"Error sending SMS: {e}" from e
