"""
PyWhatKit Service
Handles WhatsApp automation, YouTube playback, and Google search
"""

import pywhatkit
import time
from datetime import datetime, timedelta
from typing import Optional, Dict
from loguru import logger
import threading


class PyWhatKitService:
    """Wrapper for pywhatkit features"""

    def __init__(self):
        pass

    async def handle_command(self, intent: Dict[str, any]) -> str:
        """Execute pywhatkit command based on intent"""
        action = intent.get("action")
        
        try:
            if action == "play_youtube":
                query = intent.get("query", "")
                # Run in thread to avoid blocking
                threading.Thread(target=pywhatkit.playonyt, args=(query,), daemon=True).start()
                return f"Playing '{query}' on YouTube..."

            elif action == "google_search":
                query = intent.get("query", "")
                threading.Thread(target=pywhatkit.search, args=(query,), daemon=True).start()
                return f"Searching Google for '{query}'..."

            elif action == "whatsapp_message":
                phone = intent.get("phone", "")
                message = intent.get("message", "")
                
                if not phone:
                    return "I need a phone number to send the message."
                
                # Format phone number (must verify country code)
                if not phone.startswith("+"):
                    return "Please provide the phone number with country code (e.g., +91...)"

                # Schedule for 2 mins later (pywhatkit requirement) or play instantly?
                # playwhatkit.sendwhatmsg_instantly usually safer for instant
                # Using thread to not block the response
                def send_msg():
                    try:
                        import pyautogui
                        logger.info(f"Attempting to send WhatsApp message to {phone}")
                        # Use a separate thread to force Enter press after typing
                        # pywhatkit types at wait_time (+ a few seconds for typing)
                        def force_enter():
                            time.sleep(25 + 5) # wait_time + buffer for typing
                            logger.info("Forcing Enter key press...")
                            pyautogui.press('enter')
                            time.sleep(2)
                            pyautogui.press('enter') # Double tap to be sure
                        
                        threading.Thread(target=force_enter, daemon=True).start()

                        # wait_time: time to wait for WhatsApp Web to load
                        # Increase to 25s for reliability
                        # close_time: wait 10s after typing before closing (gives time to send)
                        pywhatkit.sendwhatmsg_instantly(
                            phone_no=phone, 
                            message=message, 
                            wait_time=25, 
                            tab_close=True,
                            close_time=10
                        )
                        # Fallback: pywhatkit might not press enter if timing is off
                        # We can't easily press enter here because sendwhatmsg_instantly blocks
                        # BUT tab_close=True means it waits close_time then closes.
                        # Ideally, increasing wait_time helps.
                        
                        logger.info("WhatsApp message sent successfully")
                    except Exception as e:
                        logger.error(f"WhatsApp send failed: {e}")

                if not message:
                    return f"I found the number {phone}, but what should I say? Please specify the message."

                threading.Thread(target=send_msg, daemon=True).start()
                return f"Opening WhatsApp Web to send message to {phone}: '{message}'\nPlease ensure you are logged in."

            elif action == "handwriting":
                text = intent.get("text", "")
                if not text:
                    return "I need text to convert to handwriting."
                
                output_file = "handwriting_output.png"
                pywhatkit.text_to_handwriting(text, output_file, rgb=(0, 0, 138))
                return f"Converted text to handwriting. Saved as '{output_file}'."

        except Exception as e:
            logger.error(f"PyWhatKit action failed: {e}")
            return f"Failed to execute command: {str(e)}"

        return "Unknown command."


# Global instance
pywhatkit_service = PyWhatKitService()
