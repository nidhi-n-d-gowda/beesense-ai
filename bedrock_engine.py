import json
import os
import boto3
from typing import List, Dict, Any, Optional
from datetime import datetime

class BedrockEngine:
    def __init__(self):
        self.region = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
        self.model_id = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-5-sonnet-20240620-v1:0")
        self.client = None
        
        # Check if AWS credentials exist
        if os.getenv("AWS_ACCESS_KEY_ID") and os.getenv("AWS_SECRET_ACCESS_KEY"):
            try:
                self.client = boto3.client(
                    service_name="bedrock-runtime",
                    region_name=self.region,
                    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
                )
            except Exception as e:
                print(f"AWS Bedrock client init error: {e}")

    def analyze_ambient_stream(self, transcription: str, telemetry: Dict[str, Any], recent_context: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze incoming audio transcription + wearable sensor telemetry in real-time.
        Generates proactive nudges, action item extraction, and wellness alerts.
        """
        prompt = f"""You are the AI brain of BeeSense, an intelligent ambient wearable device.
Current User Telemetry:
- Heart Rate: {telemetry.get('heart_rate', 72)} bpm (Normal baseline: 60-90)
- Movement / Activity: {telemetry.get('activity', 'stationary')}
- Ambient Noise: {telemetry.get('ambient_noise_db', 45)} dB
- Location Context: {telemetry.get('location', 'Office')}

Recent Conversational Memory Context:
{json.dumps(recent_context[-5:], indent=2) if recent_context else "None"}

New Ambient Audio Stream Input:
"{transcription}"

Your tasks:
1. Determine if this input contains key insights, tasks/action items, or critical reminders.
2. Check if heart rate or conversation sentiment indicates stress or high cognitive load.
3. Generate a proactive, subtle audio/haptic wearable nudge ONLY if necessary (keep it concise, 1-2 punchy sentences).
4. Extract structured items (category, summary, action_items, mood_detected, nudge_text, priority: low/medium/high).

Return strictly valid JSON with this schema:
{{
  "should_nudge": boolean,
  "nudge_text": string or null,
  "haptic_pattern": "gentle" | "double_tap" | "alert" | "none",
  "category": "work_meeting" | "casual_chat" | "wellness_alert" | "memory_note" | "task",
  "summary": string,
  "action_items": [string],
  "sentiment": "positive" | "neutral" | "stressed" | "excited",
  "priority": "low" | "medium" | "high"
}}
"""
        if self.client:
            try:
                body = json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 1000,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.2
                })
                response = self.client.invoke_model(
                    body=body,
                    modelId=self.model_id,
                    accept="application/json",
                    contentType="application/json"
                )
                response_body = json.loads(response.get('body').read())
                output_text = response_body['content'][0]['text']
                # Parse JSON block
                clean_json = output_text.strip()
                if clean_json.startswith("```json"):
                    clean_json = clean_json[7:-3].strip()
                elif clean_json.startswith("```"):
                    clean_json = clean_json[3:-3].strip()
                return json.loads(clean_json)
            except Exception as e:
                print(f"Bedrock invocation failed, falling back to smart simulation mode: {e}")
                return self._simulate_response(transcription, telemetry)
        else:
            return self._simulate_response(transcription, telemetry)

    def query_second_brain(self, query: str, memory_log: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Recall episodic memory from Bee wearable logs.
        """
        prompt = f"""You are the BeeSense Wearable Second Brain engine.
User Query: "{query}"

Stored Wearable Memory Stream (Timeline):
{json.dumps(memory_log, indent=2)}

Answer the user's question clearly, citing specific timestamps/events if available. If not found, indicate politely.
Return JSON:
{{
  "answer": string,
  "referenced_memories": [list of relevant memory IDs or summaries],
  "confidence": "high" | "medium" | "low"
}}
"""
        if self.client:
            try:
                body = json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 800,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1
                })
                response = self.client.invoke_model(
                    body=body,
                    modelId=self.model_id,
                    accept="application/json",
                    contentType="application/json"
                )
                response_body = json.loads(response.get('body').read())
                output_text = response_body['content'][0]['text'].strip()
                if output_text.startswith("```json"):
                    output_text = output_text[7:-3].strip()
                return json.loads(output_text)
            except Exception as e:
                print(f"Bedrock query error: {e}")
                return self._simulate_query(query, memory_log)
        else:
            return self._simulate_query(query, memory_log)

    def _simulate_response(self, text: str, telemetry: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback local smart heuristics when AWS credentials are not yet configured."""
        hr = telemetry.get('heart_rate', 72)
        text_lower = text.lower()
        
        is_stressed = hr > 100 or any(w in text_lower for w in ["deadline", "urgent", "emergency", "crisis", "pressure"])
        has_action = any(w in text_lower for w in ["remember to", "action item", "todo", "need to", "don't forget", "by friday", "meeting at"])
        
        actions = []
        if has_action:
            actions.append(f"Follow up on: {text[:60]}...")
            
        nudge_text = None
        should_nudge = False
        haptic = "none"
        category = "casual_chat"
        
        if is_stressed:
            category = "wellness_alert"
            should_nudge = True
            nudge_text = f"Elevated heart rate ({hr} bpm) detected during discussion. Take a 5-second deep breath."
            haptic = "gentle"
        elif has_action:
            category = "task"
            should_nudge = True
            nudge_text = "Captured 1 action item to your Second Brain."
            haptic = "double_tap"
        elif len(text.split()) > 8:
            category = "work_meeting"
            
        return {
            "should_nudge": should_nudge,
            "nudge_text": nudge_text,
            "haptic_pattern": haptic,
            "category": category,
            "summary": f"Context recorded: {text[:80]}",
            "action_items": actions,
            "sentiment": "stressed" if is_stressed else "neutral",
            "priority": "high" if is_stressed or has_action else "low"
        }

    def _simulate_query(self, query: str, memory_log: List[Dict[str, Any]]) -> Dict[str, Any]:
        q_lower = query.lower()
        matches = []
        for mem in memory_log:
            content = mem.get("transcription", "") + " " + mem.get("summary", "")
            if any(word in content.lower() for word in q_lower.split() if len(word) > 3):
                matches.append(mem)
                
        if matches:
            latest = matches[-1]
            return {
                "answer": f"According to your wearable log at {latest.get('timestamp', 'recently')}: \"{latest.get('transcription')}\"",
                "referenced_memories": [m.get("summary") for m in matches[:3]],
                "confidence": "high"
            }
        return {
            "answer": f"I checked your ambient memory stream, but found no direct record matching '{query}'.",
            "referenced_memories": [],
            "confidence": "low"
        }
