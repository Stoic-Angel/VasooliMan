
import asyncio
import os
import logging
from dotenv import load_dotenv
from personality_generator import PersonalityGenerator
from chat_simulator import ChatSimulator
from script_optimizer import ScriptOptimizer
import json

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables
load_dotenv(".env.local")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

def get_original_script():
    """Reads the original agent script from agent.py."""
    # This is a simplified way to get the script.
    # In a real application, you would parse the file more robustly.
    with open("agent.py", "r") as f:
        lines = f.readlines()
        script_started = False
        script_lines = []
        for line in lines:
            if "super().__init__(" in line:
                script_started = True
            if script_started:
                script_lines.append(line)
            if ")" in line and script_started and "super().__init__(" not in line:
                break
    return "".join(script_lines)

async def main():
    """Main function to run the mini pipeline."""
    if not OPENAI_API_KEY:
        logging.error("OPENAI_API_KEY not found in .env.local")
        return

    num_simulations = 5
    all_conversation_logs = []

    # 1. Initialize the components
    personality_gen = PersonalityGenerator(api_key=OPENAI_API_KEY)
    chat_sim = ChatSimulator(api_key=OPENAI_API_KEY)
    script_opt = ScriptOptimizer(api_key=OPENAI_API_KEY)

    # 2. Get the original agent script
    original_script = get_original_script()
    logging.info("--- Original Agent Script ---")
    logging.info(original_script)

    # 3. Run multiple simulations
    for i in range(num_simulations):
        logging.info(f"simulating person {i+1}")
        personality_str = await personality_gen.generate()
        conversation_log = await chat_sim.simulate(original_script, personality_str)
        all_conversation_logs.append(conversation_log)
    
    logging.info("simulations complete.")

    # 4. Optimize the script
    logging.info("--- Optimizing Agent Script ---")
    optimization_results = await script_opt.optimize(original_script, all_conversation_logs)

    # 5. Display the results
    logging.info("--- Optimization Results ---")
    try:
        results = json.loads(optimization_results)
        print(json.dumps(results, indent=4))
    except json.JSONDecodeError:
        logging.error("Failed to parse optimization results as JSON.")
        print(optimization_results)

if __name__ == "__main__":
    asyncio.run(main())
