import os
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Optional, Literal
from langchain_ollama import ChatOllama 
from langchain_core.messages import SystemMessage, HumanMessage
from valuation import ValuationEngine

# --- 1. CONFIGURATION ---
# Temperature 0.1 = Very precise, less "creative" hallucination
llm = ChatOllama(model="llama3.1", temperature=0.1)
pricer = ValuationEngine()

# --- 2. STATE DEFINITIONS ---

class CarData(TypedDict):
    model: str
    listing_price: int       # The original Avito Price
    market_value: int        # The AI's calculated "Real Value"
    year: int
    mileage: int

class AgentState(TypedDict):
    phone: str
    messages: List[str]
    stage: Literal["INIT", "WAITING_REPLY", "NEGOTIATING", "CLOSED", "ABORTED"]
    car: CarData
    language: str
    patience: int             # How many times we try before giving up
    seller_current_price: int # The latest number the seller texted

# --- 3. THE BRAIN (LOGIC & PERCEPTION) ---
BOT_NAME = os.getenv("BOT_NAME", "Hamza")
BOT_LANG = os.getenv("BOT_LANGUAGE", "MIX DARIJA AND FRENCH")

SYSTEM_DIRECTIVE = f"""
You are {BOT_NAME}, a Moroccan car buyer.
LANGUAGE: {BOT_LANG} ONLY. NO ENGLISH.
STYLE: Short, casual WhatsApp messages. 
"""

def analyze_input(state: AgentState):
    """
    Reads the seller's latest message to update the price.
    """
    # Skip if it's our turn
    if not state['messages'] or state['messages'][-1].startswith("AI:"):
        return state

    last_msg = state['messages'][-1].replace("User: ", "")
    
    # 1. Extract Price & Intent
    prompt = f"""
    Analyze: "{last_msg}"
    Output JSON only:
    {{
        "new_price": (number or null),
        "intent": "AGREE" | "REJECT" | "COUNTER" | "UNKNOWN",
        "lang": "DARIJA" | "FRENCH"
    }}
    """
    try:
        response = llm.invoke(prompt)
        # cleaning json string
        json_str = response.content.strip()
        if "{" in json_str:
            json_str = json_str[json_str.find("{"):json_str.rfind("}")+1]
        
        data = json.loads(json_str)
        
        # Update Logic
        if data.get('new_price') and data['new_price'] > 5000:
            state['seller_current_price'] = data['new_price']
            print(f"Seller moved to: {data['new_price']}")
        
        state['language'] = data.get('lang', "DARIJA")
        
    except Exception as e:
        print(f"LLM extraction error: {e}")

    # 2. Market Research (Depreciation Logic)
    # If we haven't calculated value yet, do it now.
    if state['car']['listing_price'] and not state['car'].get('market_value'):
        # Heuristic: If ML fails, assume 10% depreciation per year from a base
        # Ideally, pricer.predict_fair_value() does this.
        estimated = pricer.predict_fair_value(
            state['car']['model'], 
            state['car']['year'], 
            state['car'].get('mileage'), 
            state['car']['listing_price']
        )
        state['car']['market_value'] = estimated
        print(f"AI Research: True Market Value is {estimated} DH")

    return state

def router(state: AgentState):
    """
    Decides the next move based on the Gap Analysis.
    """
    seller_price = state.get('seller_current_price') or state['car'].get('listing_price')
    target = state['car'].get('market_value')
    
    # Safety: If we have no target, default to negotiation
    if not target or not seller_price: return "negotiate"

    # 1. The Gap Logic
    gap = seller_price - target
    percent_diff = gap / target

    print(f"Gap: {gap} DH ({percent_diff:.1%}) | Patience: {state['patience']}")

    # CASE A: Good Price (Seller is at or below Target)
    if seller_price <= target:
        return "close_success"

    # CASE B: Hopeless (Seller is > 20% over market value)
    # We don't waste time. We abort so it doesn't pollute data.
    if percent_diff > 0.20:
        return "abort_bad_price"

    # CASE C: Stagnation (We tried 4 times and they won't move)
    if state['patience'] <= 0:
        return "abort_stuck"

    # CASE D: Negotiable (Gap is small enough to argue)
    return "negotiate"

# --- 4. THE MOUTH (GENERATORS) ---

def negotiate(state: AgentState):
    current = state.get('seller_current_price') or state['car']['listing_price']
    target = state['car']['market_value']
    
    current_year = datetime.now().year
    car_age = current_year - state['car']['year'] if state['car'].get('year') else 5
    
    # Dynamic Argument Generator
    prompt = f"""
    {SYSTEM_DIRECTIVE}
    CONTEXT: 
    - Car: {state['car']['model']} ({state['car'].get('year', 'Unknown')})
    - Seller Wants: {current} DH
    - Market Value (Research): {target} DH
    
    GOAL: Convince them to lower the price.
    ARGUMENT: Use the car's age ({car_age} years old) and market depreciation.
    OFFER: Offer exactly {target} DH.
    
    Write 1 sentence. Polite but firm.
    """
    
    msg = llm.invoke(prompt).content.replace('"', '').replace("AI:", "")
    
    state['messages'].append(f"AI: {msg}")
    state['stage'] = "NEGOTIATING"
    state['patience'] -= 1 # Decrement patience
    return state

def close_success(state: AgentState):
    price = state.get('seller_current_price')
    msg = f"Safi mzyan ({price} DH). Prix raisonnable. Nji nchoufha? (I'll come see it)"
    state['messages'].append(f"AI: {msg}")
    state['stage'] = "CLOSED" # Successful deal
    return state

def abort_bad_price(state: AgentState):
    # The "Hard Pass"
    msg = "Non bezzaf a khouya. Had taman tale3 bzaf 3la souk. Lah yjib tissir."
    state['messages'].append(f"AI: {msg}")
    state['stage'] = "ABORTED" # DOES NOT COUNT IN STATS
    return state

def abort_stuck(state: AgentState):
    # The "Soft Pass" (We tried, they wouldn't budge)
    msg = "Je comprends. Walakin budget diali limité. Ila bddelti rayk 3lemny. Merci."
    state['messages'].append(f"AI: {msg}")
    state['stage'] = "ABORTED"
    return state

# --- 5. GRAPH BUILD ---

workflow = StateGraph(AgentState)
workflow.add_node("analyze", analyze_input)
workflow.add_node("negotiate", negotiate)
workflow.add_node("close_success", close_success)
workflow.add_node("abort_bad_price", abort_bad_price)
workflow.add_node("abort_stuck", abort_stuck)

workflow.set_entry_point("analyze")

workflow.add_conditional_edges(
    "analyze",
    router,
    {
        "negotiate": "negotiate",
        "close_success": "close_success",
        "abort_bad_price": "abort_bad_price",
        "abort_stuck": "abort_stuck"
    }
)

workflow.add_edge("negotiate", END)
workflow.add_edge("close_success", END)
workflow.add_edge("abort_bad_price", END)
workflow.add_edge("abort_stuck", END)

app = workflow.compile()
