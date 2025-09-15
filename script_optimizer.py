
import logging
from openai import AsyncOpenAI

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ScriptOptimizer:
    def __init__(self, api_key: str):
        self.client = AsyncOpenAI(api_key=api_key)

    async def optimize(self, original_script: str, conversation_logs: list) -> str:
        """Analyzes conversation logs and generates an improved agent script."""
        logging.info("Optimizing agent script based on conversation logs...")
        
        # Combine all conversation logs into a single string for the prompt
        formatted_logs = "\n\n---\n\n".join([
            "\n".join([f"{msg['role']}: {msg['content']}" for msg in log]) for log in conversation_logs
        ])
        
        prompt = f"""
        You are an expert in conversational AI and prompt engineering.
        Your task is to analyze a series of conversations and suggest improvements to an agent's instruction script.

        Here is the agent's original script:
        -------------------
        {original_script}
        -------------------

        Here are the logs of the conversations the agent had:
        -------------------
        {formatted_logs}
        -------------------

        Based on these conversations, please perform the following actions:

        1.  **Rate the agent's performance** on the following metrics, on a scale of 1 to 10:
            - `negotiation_effectiveness`: How well did the agent attempt to negotiate payment plans or settlements?
            - `response_relevance`: How relevant were the agent's responses to the user's queries?

        2.  **Provide actionable suggestions** for what to add or change in the original script to improve these scores.

        3.  **Estimate the impact** of your suggestions by providing the expected score for each metric after the changes are applied.

        Return your response as a JSON object with the following structure:
        {{
            "current_scores": {{
                "negotiation_effectiveness": <current_score>,
                "response_relevance": <current_score>
            }},
            "suggestions": [
                {{
                    "suggestion": "<Your suggestion for what to add or change>",
                    "reason": "<Brief reason for the suggestion>"
                }}
            ],
            "expected_scores_after_improvement": {{
                "negotiation_effectiveness": <expected_score>,
                "response_relevance": <expected_score>
            }}
        }}
        """

        response = await self.client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": prompt}
            ]
        )

        new_script_suggestions = response.choices[0].message.content
        logging.info("Script optimization complete.")
        return new_script_suggestions