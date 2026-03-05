"""
Home Assistant Integration
Control smart home devices through natural language
"""

import httpx
from typing import List, Dict, Optional
from loguru import logger

from app.config import settings
from app.models.llm import llm_client


class HomeAssistantService:
    """Service for Home Assistant integration"""
    
    def __init__(self):
        self.url = settings.HOME_ASSISTANT_URL
        self.token = settings.HOME_ASSISTANT_TOKEN
        self._client = None
        
    @property
    def is_configured(self) -> bool:
        """Check if Home Assistant is configured"""
        return bool(self.url and self.token)
    
    def _get_client(self) -> httpx.AsyncClient:
        """Get HTTP client with auth headers"""
        if not self._client:
            self._client = httpx.AsyncClient(
                base_url=self.url,
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Content-Type": "application/json"
                },
                timeout=10.0
            )
        return self._client
    
    async def get_entities(self) -> List[Dict]:
        """Get all Home Assistant entities"""
        if not self.is_configured:
            return []
        
        try:
            client = self._get_client()
            response = await client.get("/api/states")
            response.raise_for_status()
            
            entities = response.json()
            
            # Simplify entity list
            simplified = []
            for entity in entities:
                simplified.append({
                    "entity_id": entity["entity_id"],
                    "state": entity["state"],
                    "friendly_name": entity.get("attributes", {}).get("friendly_name", entity["entity_id"])
                })
            
            return simplified
            
        except Exception as e:
            logger.error(f"Failed to get Home Assistant entities: {e}")
            return []
    
    async def call_service(
        self,
        domain: str,
        service: str,
        entity_id: str,
        data: Optional[Dict] = None
    ) -> bool:
        """Call a Home Assistant service"""
        if not self.is_configured:
            return False
        
        try:
            client = self._get_client()
            
            payload = {"entity_id": entity_id}
            if data:
                payload.update(data)
            
            response = await client.post(
                f"/api/services/{domain}/{service}",
                json=payload
            )
            response.raise_for_status()
            
            logger.info(f"Called {domain}.{service} on {entity_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to call Home Assistant service: {e}")
            return False
    
    async def execute_command(self, command: str) -> str:
        """Execute a natural language home command"""
        if not self.is_configured:
            return "Home Assistant is not configured. Please set HOME_ASSISTANT_URL and HOME_ASSISTANT_TOKEN in your config."
        
        # Get available entities
        entities = await self.get_entities()
        
        if not entities:
            return "Could not retrieve devices from Home Assistant."
        
        # Format entities for LLM
        entity_list = "\n".join([
            f"- {e['friendly_name']} ({e['entity_id']}): {e['state']}"
            for e in entities[:50]  # Limit to 50 for context
        ])
        
        # Use LLM to parse command
        prompt = f"""You are a home automation assistant. Parse the user's command and respond with a JSON action.

Available devices:
{entity_list}

User command: "{command}"

Respond with JSON in this format:
{{"action": "turn_on|turn_off|toggle|set", "entity_id": "entity.id", "value": optional_value}}

If the command isn't about home control, respond with:
{{"action": "none", "message": "your helpful response"}}

Respond with only the JSON, nothing else."""

        try:
            response = await llm_client.generate(prompt)
            
            # Parse LLM response
            import json
            action_data = json.loads(response.strip())
            
            if action_data.get("action") == "none":
                return action_data.get("message", "I couldn't understand that home command.")
            
            # Execute the action
            entity_id = action_data.get("entity_id", "")
            action = action_data.get("action", "")
            
            if not entity_id or not action:
                return "I couldn't determine what action to take."
            
            # Determine domain from entity_id
            domain = entity_id.split(".")[0]
            
            # Map actions to services
            service_map = {
                "turn_on": "turn_on",
                "turn_off": "turn_off",
                "toggle": "toggle"
            }
            
            service = service_map.get(action)
            if not service:
                return f"Unknown action: {action}"
            
            success = await self.call_service(domain, service, entity_id)
            
            if success:
                # Get friendly name
                friendly = next(
                    (e["friendly_name"] for e in entities if e["entity_id"] == entity_id),
                    entity_id
                )
                return f"Done! I've {action.replace('_', ' ')} {friendly}."
            else:
                return "Failed to execute the command. Please check Home Assistant connection."
                
        except json.JSONDecodeError:
            return "I had trouble understanding that command. Could you rephrase it?"
        except Exception as e:
            logger.error(f"Home command error: {e}")
            return f"Error executing command: {str(e)}"
