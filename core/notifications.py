import os
import requests
from datetime import datetime
from typing import List, Dict, Any

# In-memory storage for simulated SMS messages (Accessible by UI for demo)
SIMULATED_SMS_STORE: List[Dict[str, Any]] = []


class NotificationService:
    """Handles dispatching SMS alerts via Twilio with robust simulated fallback."""

    def __init__(self, account_sid: str = "", auth_token: str = "", from_number: str = ""):
        self.account_sid = account_sid or os.environ.get("TWILIO_ACCOUNT_SID", "").strip()
        self.auth_token = auth_token or os.environ.get("TWILIO_AUTH_TOKEN", "").strip()
        self.from_number = from_number or os.environ.get("TWILIO_FROM_NUMBER", "").strip()

    def send_emergency_sms(
        self,
        to_phone: str,
        patient_name: str,
        hospital_name: str,
        helper_phone: str,
        live_location_url: str
    ) -> Dict[str, Any]:
        """
        Sends an emergency SMS to family contacts.
        CRITICAL PRIVACY RULE: Never includes private medical symptoms in the SMS!
        Only shares: Alert, Patient Name, Hospital Destination, Helper's phone, Live Map Link.
        """
        body = (
            f"[E-DOOT EMERGENCY ALERT] {patient_name} requires urgent medical care.\n"
            f"Assisted by bystander: {helper_phone or 'Good Samaritan'}\n"
            f"En route to: {hospital_name}\n"
            f"Live Location & Status: {live_location_url}\n"
            f"- E-Doot Emergency Network"
        )
        return self.send_sms(to_phone=to_phone, body=body, category="emergency")

    def send_adherence_missed_dose_alert(
        self,
        to_phone: str,
        patient_name: str,
        medicine_name: str,
        missed_count: int
    ) -> Dict[str, Any]:
        """Sends an alert to family when patient misses medication 3+ times."""
        body = (
            f"[E-DOOT HEALTH ALERT] Reminder: {patient_name} has missed {missed_count} consecutive "
            f"doses of {medicine_name}. Please check in on them.\n- E-Doot Adherence Watch"
        )
        return self.send_sms(to_phone=to_phone, body=body, category="reminder")

    def send_sms(self, to_phone: str, body: str, category: str = "general") -> Dict[str, Any]:
        """Attempts Twilio dispatch; falls back to simulated storage."""
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        
        # Check if Twilio credentials are configured
        if self.account_sid and self.auth_token and self.from_number:
            try:
                url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"
                resp = requests.post(
                    url,
                    data={"From": self.from_number, "To": to_phone, "Body": body},
                    auth=(self.account_sid, self.auth_token),
                    timeout=5,
                )
                if resp.status_code in [200, 201]:
                    record = {
                        "id": len(SIMULATED_SMS_STORE) + 1,
                        "timestamp": timestamp,
                        "to": to_phone,
                        "body": body,
                        "category": category,
                        "status": "Delivered via Twilio",
                        "simulated": False,
                    }
                    SIMULATED_SMS_STORE.insert(0, record)
                    return {"success": True, "provider": "twilio", "record": record}
            except Exception as e:
                print(f"[E-Doot Notification] Twilio error ({e}), falling back to simulated SMS.")

        # Fallback to in-app simulated SMS store
        record = {
            "id": len(SIMULATED_SMS_STORE) + 1,
            "timestamp": timestamp,
            "to": to_phone,
            "body": body,
            "category": category,
            "status": "Simulated Delivery (Demo)",
            "simulated": True,
        }
        SIMULATED_SMS_STORE.insert(0, record)
        print(f"\n================ [E-DOOT SIMULATED SMS] ================")
        print(f"TO: {to_phone}")
        print(f"BODY:\n{body}")
        print(f"========================================================\n")
        return {"success": True, "provider": "simulated", "record": record}

    @staticmethod
    def get_recent_messages(limit: int = 20) -> List[Dict[str, Any]]:
        """Return the latest simulated SMS messages for the demo drawer."""
        return SIMULATED_SMS_STORE[:limit]


# Global notification instance
notifier = NotificationService()
