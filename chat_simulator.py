
import logging
import json
from openai import AsyncOpenAI

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ChatSimulator:
    def __init__(self, api_key: str):
        self.client = AsyncOpenAI(api_key=api_key)

    async def simulate(self, agent_script: str, personality: str, max_turns: int = 7):
        """Simulates a chat conversation between the agent and a personality."""
        logging.info(f"Starting chat simulation...")
        
        personality_data = json.loads(personality)
        conversation_log = []
        
        # The first turn is the user's starting line
        user_message = personality_data.get('starting_line', 'Hello?')
        conversation_log.append({"role": "user", "content": user_message})

        for _ in range(max_turns):
            # Agent's turn
            agent_response = await self._get_agent_response(agent_script, conversation_log)
            conversation_log.append({"role": "assistant", "content": agent_response})

            # User's turn
            user_response = await self._get_user_response(personality, conversation_log)
            conversation_log.append({"role": "user", "content": user_response})

        logging.info("Chat simulation finished.")
        return conversation_log

    async def _get_agent_response(self, agent_script: str, history: list) -> str:
        """Gets the agent's response based on the conversation history."""
        response = await self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": agent_script},
                *history
            ]
        )
        return response.choices[0].message.content

    async def _get_user_response(self, personality: str, history: list) -> str:
        """Gets the user's response based on their personality and the history."""
        prompt = f"""
        You are role-playing as the following person:
        {personality}
        
        Based on this personality, what is your next response in the conversation?
        Keep your response short and realistic.
        """
        response = await self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": prompt},
                *history
            ]
        )
        return response.choices[0].message.content
