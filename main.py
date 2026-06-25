import os
import sys
import time
from datetime import datetime, timezone
import ssl
from dotenv import load_dotenv
from openai import OpenAI
from postgrest.exceptions import APIError
from supabase import create_client
import urllib.request
import json
import certifi

load_dotenv()
print(f"DEBUG: My URL is -> '{os.environ.get('SUPABASE_URL')}'")
POLL_INTERVAL_SEC = 5

REQUIRED_ENV = [
    "SUPABASE_URL",
    "SUPABASE_SERVICE_ROLE_KEY",
    "OPENAI_API_KEY",
]


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def log(message: str) -> None:
    print(f"[AGENT] {timestamp()} | {message}")


def log_error(message: str) -> None:
    print(f"[ERROR] {timestamp()} | {message}", file=sys.stderr)


def validate_env() -> None:
    missing = [key for key in REQUIRED_ENV if not os.environ.get(key)]
    if missing:
        log_error(f"Missing required environment variables: {', '.join(missing)}")
        log_error("Please fill in your .env file and restart the agent.")
        sys.exit(1)


validate_env()

supabase = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_SERVICE_ROLE_KEY"],
)

openai_client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

SYSTEM_PROMPT = (
    "You are a medical triage AI. Read the patient issue and extract the required medical specialty. "
    "You must reply with ONLY ONE of these exact phrases, with no other text or punctuation: "
    "'Wound Care', 'IV', or 'Pediatrics'."
)


def extract_specialty(patient_issue: str) -> str:
    log("Sending patient issue to OpenAI for specialty extraction...")

    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": patient_issue},
        ],
        max_tokens=10,
        temperature=0,
    )

    specialty = response.choices[0].message.content.strip()
    log(f"AI extracted specialty: {specialty}")
    return specialty


def find_clinician(specialty: str) -> dict | None:
    log(f'Searching clinicians table for specialty: "{specialty}"...')

    try:
        response = (
            supabase.table("clinicians")
            .select("*")
            .ilike("specialty", specialty)
            .limit(1)
            .execute()
        )
    except APIError as err:
        raise RuntimeError(f"Clinician lookup failed: {err}") from err

    data = response.data or []
    if not data:
        return None

    clinician = data[0]
    log(f"Found clinician: {clinician['name']} (phone: {clinician['phone']})")
    return clinician


def assign_request(request_id: int, specialty: str, clinician_name: str) -> None:
    log(f"Updating request #{request_id} in Supabase...")

    try:
        supabase.table("requests").update(
            {
                "required_specialty": specialty,
                "assigned_doctor": clinician_name,
                "status": "assigned",
            }
        ).eq("id", request_id).execute()
    except APIError as err:
        raise RuntimeError(f"Request update failed: {err}") from err

    log(
        f"Request #{request_id} assigned to {clinician_name} ({specialty} specialist)"
    )

def notify_n8n(request_id, patient_issue, specialty, clinician_name):
    log("Sending dispatch alert to n8n...")
    
    url = "https://poohrin.app.n8n.cloud/webhook-test/fed10958-3179-4efa-b59e-aa72a460cd07" 
    
    payload = {
        "request_id": request_id,
        "patient_issue": patient_issue,
        "required_specialty": specialty,
        "assigned_doctor": clinician_name
    }
    
    req = urllib.request.Request(
        url, 
        data=json.dumps(payload).encode('utf-8'), 
        headers={'Content-Type': 'application/json'}
    )
    
    try:
        # The proper way: create a secure context using verified Mozilla certificates
        context = ssl.create_default_context(cafile=certifi.where())
        urllib.request.urlopen(req, context=context)
        log(f"Successfully pinged n8n to dispatch {clinician_name}!")
    except Exception as err:
        log_error(f"Failed to ping n8n: {err}")

def process_request(request: dict) -> None:
    request_id = request["id"]
    patient_issue = request["patient_issue"]

    print("---")
    log(f"Processing request #{request_id}")
    log(f'Patient issue: "{patient_issue}"')

    specialty = extract_specialty(patient_issue)
    clinician = find_clinician(specialty)

    if not clinician:
        log_error(
            f'No clinician found for specialty "{specialty}". Skipping request #{request_id}.'
        )
        try:
            supabase.table("requests").update(
                {"status": "manual_review"}
            ).eq("id", request_id).execute()
        except Exception as err:
            log_error(f"Failed to move request #{request_id} to manual review: {err}")
            
        print("---")
        return

    assign_request(request_id, specialty, clinician["name"])
    notify_n8n(request_id, patient_issue, specialty, clinician["name"])
    print("---")


def poll() -> None:
    log("Polling Supabase for pending requests...")

    try:
        response = (
            supabase.table("requests")
            .select("*")
            .eq("status", "pending")
            .order("id")
            .execute()
        )
    except APIError as err:
        log_error(f"Supabase query failed: {err}")
        return

    data = response.data or []
    if not data:
        log("No pending requests. Waiting...")
        return

    log(f"Found {len(data)} pending request(s). Starting triage...")

    for request in data:
        try:
            process_request(request)
        except Exception as err:
            log_error(f"Failed to process request #{request['id']}: {err}")
            print("---")


def main() -> None:
    print("")
    log("========================================")
    log("  MEDICAL TRIAGE AGENT — STARTING UP")
    log("========================================")
    log(f"Poll interval: every {POLL_INTERVAL_SEC} seconds")
    log(f"Supabase URL: {os.environ['SUPABASE_URL']}")
    log("OpenAI model: gpt-4o-mini")
    log("Watching table: requests (status = 'pending')")
    log("========================================")
    print("")

    while True:
        poll()
        time.sleep(POLL_INTERVAL_SEC)


if __name__ == "__main__":
    main()
