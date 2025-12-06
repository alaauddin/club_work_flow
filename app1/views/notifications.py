import threading
import requests
import logging

logger = logging.getLogger(__name__)

def send_message(number, message):
    def send():
        data = {
            "User": "Altarfeehi",
            "Pass": "Altarfeehi@277",
            "Method": "Chat",
            "To": str(number),
            "Body": str(message)
        }
        try:
            response = requests.post(
                url="http://185.216.203.97:8070/AWE/Api/index.php",
                data=data,
                timeout=20
            )
            print(response.json())
        except Exception as e:
            print(f"Message sending failed: {e}")
    
    threading.Thread(target=send).start()
