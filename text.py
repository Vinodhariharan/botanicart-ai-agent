import google.generativeai as genai
import os

# --- Configuration (from your provided code) ---
# Ensure your API key is set as an environment variable or passed securely
# For example, in your terminal before running the script:
# export GEMINI_API_KEY="your_api_key_here"
# Or if you're running on Google Cloud, credentials might be handled automatically.
genai.configure(api_key=os.environ["GEMINI_API_KEY"])

# --- Model to Test ---
MODEL_NAME = "gemini-1.5-flash" # Or "gemini-1.5-pro-latest" or "gemini-1.5-flash" etc.

# --- Sample Input (tailored for your chatbot's needs) ---
# This is a basic example. In your actual bot, you'd fetch product data
# and format it appropriately before sending it with the user's query.
sample_query = "Recommend a low maintenance plant for my office under $30."

# Example product data that could be passed (truncated for brevity)
# In a real scenario, you'd fetch this from your Firestore and format it.
sample_product_data = """
Product Catalog (relevant subset):
- Plant: Succulent Collection, Price: $24.99, Maintenance: Very Low, Light: Bright Indirect, Toxicity: Non-toxic.
- Plant: Chinese Money Plant, Price: $23.99, Maintenance: Low, Light: Medium Indirect, Toxicity: Non-toxic.
- Plant: Snake Plant, Price: $24.99, Maintenance: Very Low, Light: Low to Bright, Toxicity: Mildly toxic to pets.
- Plant: Fiddle Leaf Fig, Price: $75.00, Maintenance: High, Light: Bright Indirect, Toxicity: Mildly toxic.
- Plant: ZZ Plant, Price: $28.00, Maintenance: Very Low, Light: Low to Medium Indirect, Toxicity: Toxic.
"""

# Combine the product data and the user query
# This is how you'd leverage the large context window
prompt_content = f"""
You are a helpful plant recommendation bot for BotaniCart.
Based on the following product catalog information and the user's request, provide a helpful and concise recommendation.
If no suitable product is found, suggest how the user can refine their search.

{sample_product_data}

User Query: {sample_query}
"""

print(f"--- Testing Model: {MODEL_NAME} ---")
print(f"Sending prompt:\n{prompt_content}\n")

try:
    # Get the model instance
    model = genai.GenerativeModel(MODEL_NAME)

    # Generate content
    response = model.generate_content(prompt_content)

    # Print the model's response
    print("--- Model Response ---")
    print(response.text)

    # You can also access other information if available, e.g., prompt feedback
    # print("\n--- Prompt Feedback ---")
    # print(response.prompt_feedback)

except genai.types.StopCandidateException as e:
    # This specific exception means the model stopped generating due to safety filters
    print(f"Generation stopped prematurely due to safety filters: {e}")
except Exception as e:
    # Catch any other general errors (e.g., API key issues, network problems, quota)
    print(f"An error occurred during content generation: {e}")