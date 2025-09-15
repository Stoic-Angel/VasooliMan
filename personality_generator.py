
import logging
from openai import AsyncOpenAI

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class PersonalityGenerator:
    def __init__(self, api_key: str):
        self.client = AsyncOpenAI(api_key=api_key)

    async def generate(self):
        """Generates a single, random debtor personality."""
        logging.info("Generating a new debtor personality...")
        
        prompt = """
        Create a brief, realistic personality profile for a credit card defaulter.
        Include the following details:
        - Name
        - Age
        - Occupation
        - A short background explaining why they defaulted (e.g., job loss, medical emergency).
        - Their current financial situation (e.g., struggling, looking for work).
        - Their attitude towards the debt (e.g., cooperative, evasive, anxious).
        - A starting line for the conversation (what they would say when they pick up the phone).
        
        Present the output as a JSON object.
        """

        response = await self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": prompt}],
            response_format={"type": "json_object"}
        )
        
        personality = response.choices[0].message.content
        logging.info(f"Generated personality: {personality}")
        return personality
