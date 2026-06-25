# CareRoute: Autonomous Medical Dispatch Agent

An AI-powered triage and dispatch pipeline built to process patient intake, autonomously determine required medical specialties, and trigger instant doctor deployments. 

*Built from scratch as a solo hackathon project.*

## The Goal
In high-pressure medical environments, routing urgent requests to the right specialist takes critical time. CareRoute acts as a middle-layer "brain." It reads raw patient intake text, uses LLMs to extract the required specialty, updates the database, and instantly fires webhooks to notify the correct doctor—completely hands-off.

### Screenshot of output

<img width="832" height="342" alt="Screenshot 2026-06-25 at 23 09 37" src="https://github.com/user-attachments/assets/9838ffcd-027b-48bc-9d5e-a8957ea2168d" />


![CareRoute Terminal Output](link-to-your-terminal-screenshot-here.png)


## Tech Stack & Architecture
This project proves out a modern, event-driven AI architecture rather than just a single script:

* **The Brain:** `Python 3` + `OpenAI API` (gpt-4o-mini)
* **The Database:** `Supabase` (PostgreSQL) for state management and record keeping.
* **The Automation Loop:** `n8n` for front-end form intake and back-end webhook email dispatch.

### How it Works (The Pipeline)
1. **Intake:** A patient or nurse submits a plain-text issue via an n8n web form.
2. **Polling & Extraction:** The Python Agent continuously polls Supabase for `'pending'` requests. It sends the raw text to OpenAI, forcing it to return a strictly formatted medical specialty (e.g., *Pediatrics*, *Wound Care*).
3. **Assignment:** The Agent queries the Supabase `clinicians` table to find an available doctor matching that exact specialty and updates the request to `'assigned'`.
4. **Dispatch:** The instant the doctor is assigned, the Python script fires a secure payload to an n8n webhook, which instantly blasts an email/SMS to the doctor.

<img width="543" height="270" alt="Screenshot 2026-06-25 at 23 12 09" src="https://github.com/user-attachments/assets/38c2bbd8-6234-405d-b859-ee7aaf17a8e9" />

<img width="528" height="268" alt="Screenshot 2026-06-25 at 23 25 34" src="https://github.com/user-attachments/assets/955873e2-2152-4903-91d0-3241a93d56e7" />


## Quick Start (Run it Locally)

If you want to run this locally follow the steps below

### 1. Clone the repository and create a virtual environemnt and install required dependencies 

### 2. Add your API Keys
Create a .env file in the root directory and add your credentials. (See .env.example for the required format)

### 3. Run the agent 
python3 main.py

### License
This project is open-source and available under the MIT License.
