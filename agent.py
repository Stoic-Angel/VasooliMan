#--------------------------------
#--------- IMPORTS --------------
#--------------------------------

from __future__ import annotations
import asyncio
import logging
from dotenv import load_dotenv
import json
import multiprocessing
import os
from typing import Any
from livekit import rtc, api
from livekit.agents import (
    AgentSession,
    Agent,
    JobContext,
    function_tool,
    RunContext,
    get_job_context,
    cli,
    WorkerOptions,
    RoomInputOptions,
    ConversationItemAddedEvent,
    UserInputTranscribedEvent,
)
from livekit.plugins import (
    deepgram,
    openai,
    cartesia,
    silero,
    noise_cancellation # noqa: F401
)
from livekit.plugins.turn_detector.english import EnglishModel



load_dotenv(".env.local")
logger = logging.getLogger("outbound-caller")
logger.setLevel(logging.INFO)
outbound_trunk_id = os.getenv("SIP_OUTBOUND_TRUNK_ID") #something was off, wrote this just to ensure it's set

# to handle `PicklingError: Can't pickle <type 'function'>`
try:
    multiprocessing.set_start_method('fork', force=True)
except RuntimeError:
    pass


#------------------------
#---------AGENT----------
#------------------------


class VasooliMan(Agent):
    def __init__(
        self,
        *,
        customer_name: str,
        account_number: str,
        outstanding_amount: str,
        due_date: str,
        card_type: str,
        dial_info: dict[str, Any],
    ):
        super().__init__(
            instructions=f"""
            You are a professional debt collection representative for a major bank. Your interface with users will be voice.
            You are calling {customer_name} regarding their overdue credit card bill. YOU HAVE TO RETURN ANSWERS THAT A PERSON CAN SPEAK OUT LOUD.
            DO NOT RETURN MARKDOWN FORMATTING.
            
            FETCHED DETAILS:
            - Customer: {customer_name}
            - Account: {account_number}
            - Card Type: {card_type}
            - Outstanding Amount: ${outstanding_amount}
            - Payment Due Date: {due_date}
            
            NEEDED BEHAVIOR:
            - Always identify yourself and the company at the start.
            - Be professional, respectful, and empathetic.
            - Verify you're speaking with the right person before discussing debt details.
            - Offer payment options (full amount, minimum payment, or payment plan).
            - Respect customer requests to end the call.
            
            GOALS:
            1. Verify customer identity.
            2. Inform about the overdue credit card account.
            3. Discuss payment options and try to secure a payment commitment.
            4. If no immediate payment, provide clear next steps.
            
            HOW TO HANDLE THESE EDGE CASES:
            - If customer disputes debt: Use handle_payment_dispute tool to log the dispute.
            - If customer requests no more calls: Use handle_do_not_call_request tool.
            - If customer is silent after pickup: Use handle_silent_call tool to prompt for a response.
            - If customer is hostile: Stay calm, and document the interaction.
            - If interrupted: Acknowledge the interruption and continue the conversation naturally.
            
            HOW TO START THE CONVERSATION:
            - If user says "Hello?": Immediately respond with your name and the bank's name.
            - If user is silent: Wait 3 seconds then say "Hello, is this {customer_name}?"
            - If background noise: Acknowledge it and ask if they can hear you clearly.
            
            ALWAYS MAINTAIN A HELPFUL, SOLUTION-ORIENTED APPROACH.
            """
        )
        # Store customer information
        self.customer_name = customer_name
        self.account_number = account_number
        self.outstanding_amount = outstanding_amount
        self.due_date = due_date
        self.card_type = card_type
        self.participant: rtc.RemoteParticipant | None = None
        self.dial_info = dial_info

    def set_participant(self, participant: rtc.RemoteParticipant):
        self.participant = participant

    # the agent wasn't hanging up the call, so I added this func
    async def hangup(self):
        """Function to hang up the call by deleting the room"""
        logger.info(f"hanging up the call for {self.participant.identity}")
        job_ctx = get_job_context()
        await job_ctx.api.room.delete_room(
            api.DeleteRoomRequest(
                room=job_ctx.room.name,
            )
        )


#------------------------
#---------TOOLS----------
#------------------------

    @function_tool()
    async def end_call(self, ctx: RunContext):
        """Function to end the call, call this when user wants to end the call"""
        logger.info(f"ending the call for {self.participant.identity}")

        # lets the agent finish speaking before ending the call
        current_speech = ctx.session.current_speech
        if current_speech:
            await current_speech.wait_for_playout()

        await asyncio.sleep(1)
        await self.hangup()

    
    @function_tool()
    async def setup_payment_plan(
        self,
        ctx: RunContext,
        monthly_amount: str,
        duration_months: str,
    ):
        """Set up a payment plan for the customer

        Args:
            monthly_amount: The monthly payment amount the customer can afford
            duration_months: Number of months for the payment plan
        """
        logger.info(
            f"setting up payment plan for {self.participant.identity}: ${monthly_amount}/month for {duration_months} months"
        )
        await asyncio.sleep(2)
        return {
            "status": "approved",
            "plan_id": "PLAN789012345",
            "message": f"Payment plan approved: ${monthly_amount} per month for {duration_months} months"
        }

    @function_tool()
    async def schedule_callback(
        self,
        ctx: RunContext,
        callback_date: str,
        callback_time: str,
    ):
        """Schedule a callback with the same customer if explicitly requested, or if the user says they're busy

        Args:
            callback_date: The date for the callback
            callback_time: The preferred time for the callback
        """
        logger.info(
            f"scheduling callback for {self.participant.identity} on {callback_date} at {callback_time}"
        )
        return {
            "status": "scheduled",
            "callback_id": "CB456789012",
            "message": f"Callback scheduled for {callback_date} at {callback_time}"
        }

    @function_tool()
    async def process_payment(
        self,
        ctx: RunContext,
        amount: str,
        payment_method: str,
    ):
        """Process a payment from the customer

        Args:
            amount: The payment amount the customer wants to make
            payment_method: The payment method (credit_card, bank_transfer, etc.)
        """
        logger.info(
            f"processing payment of ${amount} via {payment_method} for {self.participant.identity}"
        )
        await asyncio.sleep(2)
        return {
            "status": "success",
            "message": f"Payment of ${amount} processed successfully via {payment_method}"
        }

    @function_tool()
    async def handle_payment_dispute(
        self,
        ctx: RunContext,
        dispute_reason: str,
    ):
        """Handle customer dispute about the debt

        Args:
            dispute_reason: The reason customer gives for disputing (already paid, not theirs, etc.)
        """
        logger.info(f"Payment dispute from {self.participant.identity}: {dispute_reason}")
        return {
            "status": "disputed",
            "dispute_id": "DISP123456789",
            "message": "Dispute logged. Account will be reviewed within 3-5 business days"
        }

    @function_tool()
    async def handle_silent_call(self, ctx: RunContext):
        """Handle cases where user picks up but doesn't respond"""
        logger.info(f"Silent call detected for {self.participant.identity}")
        await ctx.session.generate_reply(
            instructions="Try to get a response with 'Hello? Is anyone there?' If still no response, end call"
        )

    @function_tool()
    async def detected_answering_machine(self, ctx: RunContext):
        """Called when the call reaches voicemail. Use this tool AFTER you hear the voicemail greeting"""
        logger.info(f"detected answering machine for {self.participant.identity}")
        await self.hangup()

async def entrypoint(ctx: JobContext):
    logger.info(f"JOB RECEIVED: connecting to room {ctx.room.name}")
    logger.info(f"JOB METADATA: {ctx.job.metadata}")
    await ctx.connect()
    dial_info = json.loads(ctx.job.metadata)
    participant_identity = phone_number = dial_info["phone_number"]


    customer_name = dial_info.get("customer_name", "Valued Customer")
    account_number = dial_info.get("account_number", "ABC123")
    outstanding_amount = dial_info.get("outstanding_amount", "1000")
    due_date = dial_info.get("due_date", "September 15, 2025")
    card_type = dial_info.get("card_type", "Visa")
    

    agent = VasooliMan(
        customer_name=customer_name,
        account_number=account_number,
        outstanding_amount=outstanding_amount,
        due_date=due_date,
        card_type=card_type,
        dial_info=dial_info,
    )

    session = AgentSession(
        turn_detection=EnglishModel(),
        vad=silero.VAD.load(),
        stt=deepgram.STT(),
        tts=cartesia.TTS(voice="79f8b5fb-2cc8-479a-80df-29f7a7cf1a3e"),
        llm=openai.LLM(model="gpt-4o-mini"),
    )
    
    # made these event handlers to debug the conversation flow, not needed for production
    @session.on("user_input_transcribed")
    def on_user_input_transcribed(event: UserInputTranscribedEvent):
        async def _log_transcript():
            logger.info(f"User speech committed: {event.transcript}")
        
        asyncio.create_task(_log_transcript())
    
    @session.on("conversation_item_added") 
    def on_agent_speech_committed(event: ConversationItemAddedEvent):
        async def _log_item():
            logger.info(f"Agent speech committed: {event.item.text_content}")

        asyncio.create_task(_log_item())
    
    @session.on("user_state_changed")
    def on_user_state_changed(state: str):
        async def _log_state():
            logger.info(f"User state changed: {state}")
        
        asyncio.create_task(_log_state())
    
    @session.on("agent_state_changed")
    def on_agent_state_changed(state: str):
        async def _log_state():
            logger.info(f"Agent state changed: {state}")

        asyncio.create_task(_log_state())

    # this starts the session first before dialing, to ensure that when the user picks up
    # the agent does not miss anything the user says
    session_started = asyncio.create_task(
        session.start(
            agent=agent,
            room=ctx.room,
            room_input_options=RoomInputOptions(
                # enable Krisp background voice and noise removal
                noise_cancellation=noise_cancellation.BVCTelephony(),
            ),
        )
    )

    # this starts dialing the user
    logger.info(f"Creating SIP participant for {phone_number} with trunk {outbound_trunk_id}") 
    try:
        await ctx.api.sip.create_sip_participant(
            api.CreateSIPParticipantRequest(
                room_name=ctx.room.name,
                sip_trunk_id=outbound_trunk_id,
                sip_call_to=phone_number,
                participant_identity=participant_identity,
                wait_until_answered=True,
            )
        )
        logger.info("SIP participant created successfully")

        await session_started
        participant = await ctx.wait_for_participant(identity=participant_identity)
        logger.info(f"participant joined: {participant.identity}")

        agent.set_participant(participant)


        logger.info("Starting conversation with initial greeting")
        try:
            await session.generate_reply(
                instructions="Introduce yourself with this greeting: 'Hi, I'm Alex from the Bank of America'. Then, ask if you are speaking with {customer_name} to verify their identity before proceeding."
            )
            logger.info("Initial greeting sent successfully")
        except Exception as e:
            logger.error(f"Error sending initial greeting: {e}")
        

        # this keeps the conversation alive
        try:
            await session.wait_for_completion()
        except Exception as e:
            logger.error(f"Session error: {e}")

        # Monitor for call disconnect and timeout (background task)
        call_start_time = asyncio.get_event_loop().time()
        
        async def monitor_call():
            """Monitor call for disconnects and timeouts"""
            max_call_duration = 300
        
        monitor_task = asyncio.create_task(monitor_call())

    except api.TwirpError as e:
        logger.error(
            f"error creating SIP participant: {e.message}, "
            f"SIP status: {e.metadata.get('sip_status_code')} "
            f"{e.metadata.get('sip_status')}"
        )
        logger.error(f"Full error details: {e}")
        ctx.shutdown()
    except Exception as e:
        logger.error(f"Unexpected error creating SIP participant: {e}")
        logger.error(f"Error type: {type(e)}")
        ctx.shutdown()

if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            agent_name="vasooli-man",
        )
    )