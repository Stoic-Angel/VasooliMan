## VasooliMan

Voice credit card debt-collection agent using LiveKit Agents (STT/TTS/LLM) with a small simulation/optimization pipeline powered by OpenAI.

### Features
- Live, phone-based agent that dials via SIP trunk and talks using STT (Deepgram), TTS (Cartesia), and LLM (OpenAI)
- Simple mini pipeline to simulate conversations and suggest script improvements

### Setup
```bash
uv venv .venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

Create `.env.local` in the project root, follow the example and add all the keys

### Run the outbound caller agent
This starts a LiveKit Agents worker. It dials the phone number provided in the job metadata and drives the call.

```bash
uv run agent.py
```

Submit a job to the worker (via LiveKit Agents API/Console) with JSON metadata like:
```json
{
  "phone_number": "+15551234567",
  "customer_name": "John Doe",
  "account_number": "ACC123",
  "outstanding_amount": "1200",
  "due_date": "September 30, 2025",
  "card_type": "Visa"
}
```

Notes:
- The agent uses `silero.VAD`, `EnglishModel` turn detection, Deepgram STT, Cartesia TTS, and OpenAI `gpt-4o-mini`.
- It reads env from `.env.local`.

### Run the mini pipeline (simulation + optimization)
Generates synthetic debtor personalities, simulates chats against the current agent script, and asks OpenAI to produce improvement suggestions.

```bash
uv run run_mini_pipeline.py
```


### Key files
- `agent.py`: LiveKit agent worker; places/handles calls
- `run_mini_pipeline.py`: Orchestrates personality generation, chat simulation, and script optimization
- `personality_generator.py`, `chat_simulator.py`, `script_optimizer.py`: Pipeline components
- `requirements.txt`: Dependencies

### Troubleshooting
- Ensure all API keys and `SIP_OUTBOUND_TRUNK_ID` are set in `.env.local`.
- Verify your SIP trunk is active and callable in LiveKit.


