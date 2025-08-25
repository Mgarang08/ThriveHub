from flask import Flask, request, jsonify
from flask_cors import CORS
import openai
import os
from dotenv import load_dotenv
import re
from pathlib import Path
import json

load_dotenv()

app = Flask(__name__)
CORS(app)

openai.api_key = os.getenv('OPENAI_API_KEY')

user_progress = {}

DATA_FILE = Path("pages/budgeter_state.json")
GOAL_FILE = Path("pages/budgeter_goal.json")
SETTINGS_FILE = Path("pages/budgeter_settings.json")
TRANSACTIONS_FILE = Path("pages/budgeter_transactions.jsonl")

def load_budget_data():
    if DATA_FILE.exists():
        try:
            d = json.loads(DATA_FILE.read_text())
            account = d.get("account", 0.0)
            savings = d.get("savings", 0.0)
        except: pass

    goal = {}
    if GOAL_FILE.exists():
        try:
            goal = json.loads(GOAL_FILE.read_text())
        except: pass

    auto_save = 0.0
    if SETTINGS_FILE.exists():
        try:
            d = json.loads(SETTINGS_FILE.read_text())
            auto_save = d.get("auto_save_percent", 0.0)
        except: pass

    txns = []
    if TRANSACTIONS_FILE.exists():
        for line in TRANSACTIONS_FILE.read_text().splitlines():
            try:
                txns.append(json.loads(line))
            except: continue

    return {
        "account": account,
        "savings": savings,
        "goal": goal,
        "auto_save_percent": auto_save,
        "transactions": txns
    }

@app.route('/api/anxiety-copilot', methods=['POST'])
def anxiety_copilot():
    try:
        data = request.json
        user_id = data.get('user_id', 'default')
        message = data.get('message', '')
        
        system_prompt = """You are Anxiety Copilot, a supportive chatbot for teenagers. 
        You help them manage stress, anxiety, and overwhelming emotions. 
        Provide short, practical techniques for emotional regulation.
        Be empathetic, encouraging, and age-appropriate.
        Suggest breathing exercises, grounding techniques, or positive reframing.
        Keep responses under 3 sentences."""
        
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ],
            temperature=0.7,
            max_tokens=150
        )
        
        reply = response.choices[0].message.content
        
        if user_id not in user_progress:
            user_progress[user_id] = {
                "total_xp": 0, 
                "anxiety_xp": 0,
                "cooking_xp": 0, 
                "budget_xp": 0,
                "study_xp": 0,
                "streak": 0
            }
        
        xp_gained = 10
        user_progress[user_id]["anxiety_xp"] += xp_gained
        user_progress[user_id]["total_xp"] += xp_gained
        user_progress[user_id]["streak"] += 1
        
        return jsonify({
            "reply": reply, 
            "xp_gained": xp_gained,
            "total_xp": user_progress[user_id]["total_xp"],
            "anxiety_xp": user_progress[user_id]["anxiety_xp"],
            "streak": user_progress[user_id]["streak"]
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/pocket-chef', methods=['POST'])
def pocket_chef():
    try:
        data = request.json
        user_id = data.get('user_id', 'default')
        ingredients = data.get('ingredients', [])
        
        system_prompt = """You are a chef assistant for teenagers. 
        Create simple recipes using only 3-5 common ingredients.
        Recipes should take 15 minutes or less to prepare. In the end, 
        say ready to serve
        Format your response as: 
        DISH NAME: [Name]
        INGREDIENTS: [List]
        STEPS: [Numbered steps]
        TIME: [X minutes]"""
        
        user_message = f"Create a recipe using these ingredients: {', '.join(ingredients)}"
        
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.8,
            max_tokens=300
        )
        
        recipe = response.choices[0].message.content
        
        if user_id not in user_progress:
            user_progress[user_id] = {
                "total_xp": 0, 
                "anxiety_xp": 0,
                "cooking_xp": 0, 
                "budget_xp": 0,
                "study_xp": 0,
                "streak": 0
            }

        xp_gained = 15
        user_progress[user_id]["cooking_xp"] += xp_gained
        user_progress[user_id]["total_xp"] += xp_gained
        
        return jsonify({
            "recipe": recipe,
            "xp_gained": xp_gained,
            "total_xp": user_progress[user_id]["total_xp"],
            "cooking_xp": user_progress[user_id]["cooking_xp"]
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/budget-buddy', methods=['POST'])
def budget_buddy():
    try:
        data = request.json
        user_id = data.get('user_id', 'default')
        command = data.get('command', '').strip()

        with open("budgeter_unknown_commands.txt", "a", encoding="utf-8") as f:
            if command:
                f.write(f"{user_id}: {command}\n")

        budget_data = load_budget_data()
        
        system_prompt = """You are a financial advisor for teenagers. 
        Analyze their spending habits and provide helpful, non-judgmental advice.
        Suggest ways to save money and make better spending decisions.
        Keep your response under 4 sentences and focus on one key insight."""
        
        user_message = f"""
        Here are the user’s balances and budget:
        Account balance: {budget_data['account']}
        Savings balance: {budget_data['savings']}
        Auto-save: {budget_data['auto_save_percent']}%
        Goal: {budget_data['goal']}
        Transactions: {budget_data['transactions'][-10:]}

        Latest command: {command}
        """
        
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.7,
            max_tokens=200
        )
        
        advice = response.choices[0].message.content
        
        if user_id not in user_progress:
            user_progress[user_id] = {
                "total_xp": 0, 
                "anxiety_xp": 0,
                "cooking_xp": 0, 
                "budget_xp": 0,
                "study_xp": 0,
                "streak": 0
            }

        xp_gained = 12
        user_progress[user_id]["budget_xp"] += xp_gained
        user_progress[user_id]["total_xp"] += xp_gained
        
        return jsonify({
            "advice": advice,
            "xp_gained": xp_gained,
            "total_xp": user_progress[user_id]["total_xp"],
            "budget_xp": user_progress[user_id]["budget_xp"],
            "budget": budget_data
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/progress/<user_id>', methods=['GET'])
def get_progress(user_id):
    progress = user_progress.get(user_id, {
        "total_xp": 0,
        "anxiety_xp": 0,
        "cooking_xp": 0,
        "budget_xp": 0,
        "study_xp": 0,
        "streak": 0
    })
    
    return jsonify({
        "user_id": user_id,
        "progress": progress
    })

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "message": "Independence Arcade API is running!"})

if __name__ == '__main__':
    app.run(debug=True, port=5000, host='0.0.0.0')