"""
Web Services
Free real-time data: weather (wttr.in), news (Google News RSS)
"""

import httpx
import re
from typing import Optional, List, Dict
from loguru import logger
from datetime import datetime


class WebServices:
    """Fetches real-time data from free APIs (no API keys needed)"""

    def __init__(self):
        self.timeout = 10.0

    async def get_weather(self, location: str = "auto") -> Optional[str]:
        """Get weather using wttr.in (free, no API key)"""
        try:
            # wttr.in auto-detects location by IP if no location specified
            url = f"https://wttr.in/{location}?format=j1"
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers={"User-Agent": "Ira-Assistant"})
                response.raise_for_status()
                data = response.json()

            current = data.get("current_condition", [{}])[0]
            area = data.get("nearest_area", [{}])[0]

            city = area.get("areaName", [{}])[0].get("value", "Unknown")
            country = area.get("country", [{}])[0].get("value", "")
            temp_c = current.get("temp_C", "?")
            temp_f = current.get("temp_F", "?")
            feels_like_c = current.get("FeelsLikeC", "?")
            humidity = current.get("humidity", "?")
            desc = current.get("weatherDesc", [{}])[0].get("value", "Unknown")
            wind_kmph = current.get("windspeedKmph", "?")
            wind_dir = current.get("winddir16Point", "")

            # Get forecast
            forecast_lines = []
            for day in data.get("weather", [])[:3]:
                date = day.get("date", "")
                max_c = day.get("maxtempC", "?")
                min_c = day.get("mintempC", "?")
                desc_day = day.get("hourly", [{}])[4].get("weatherDesc", [{}])[0].get("value", "") if day.get("hourly") else ""
                forecast_lines.append(f"  {date}: {desc_day}, {min_c}°C - {max_c}°C")

            forecast = "\n".join(forecast_lines)

            return (
                f"📍 Location: {city}, {country}\n"
                f"🌡️ Temperature: {temp_c}°C ({temp_f}°F), feels like {feels_like_c}°C\n"
                f"☁️ Conditions: {desc}\n"
                f"💧 Humidity: {humidity}%\n"
                f"💨 Wind: {wind_kmph} km/h {wind_dir}\n"
                f"📅 Forecast:\n{forecast}"
            )

        except Exception as e:
            logger.error(f"Weather fetch failed: {e}")
            return None

    async def get_news(self, query: str = "", num_results: int = 5) -> Optional[str]:
        """Get news using Google News RSS (free, no API key)"""
        try:
            if query:
                url = f"https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"
            else:
                url = "https://news.google.com/rss?hl=en-IN&gl=IN&ceid=IN:en"

            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                response = await client.get(url)
                response.raise_for_status()

            # Parse RSS XML simply
            items = re.findall(r'<item>(.*?)</item>', response.text, re.DOTALL)

            news_items = []
            for item in items[:num_results]:
                title = re.search(r'<title>(.*?)</title>', item)
                pub_date = re.search(r'<pubDate>(.*?)</pubDate>', item)
                source = re.search(r'<source[^>]*>(.*?)</source>', item)

                title_text = title.group(1) if title else "No title"
                # Clean CDATA and HTML
                title_text = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', title_text)
                title_text = re.sub(r'<[^>]+>', '', title_text)

                date_text = pub_date.group(1) if pub_date else ""
                source_text = source.group(1) if source else ""

                entry = f"• {title_text}"
                if source_text:
                    entry += f" ({source_text})"
                if date_text:
                    # Simplify date
                    try:
                        dt = datetime.strptime(date_text.strip(), "%a, %d %b %Y %H:%M:%S %Z")
                        entry += f" - {dt.strftime('%b %d, %Y')}"
                    except:
                        pass

                news_items.append(entry)

            if news_items:
                header = f"📰 Latest News" + (f' about "{query}"' if query else "") + ":\n"
                return header + "\n".join(news_items)

            return None

        except Exception as e:
            logger.error(f"News fetch failed: {e}")
            return None


    def detect_intent(self, message: str) -> Dict[str, any]:
        """Detect if the message needs real-time data"""
        msg = message.lower().strip()

        # Weather keywords
        weather_words = ['weather', 'temperature', 'forecast', 'rain', 'sunny', 'cloudy',
                         'humid', 'wind', 'storm', 'snow', 'hot', 'cold outside',
                         'climate today', 'mausam', 'barish']
        if any(w in msg for w in weather_words):
            # Try to extract location
            location = ""
            loc_match = re.search(r'(?:in|at|for|of)\s+([a-zA-Z\s]+?)(?:\?|$|\.|\,)', msg)
            if loc_match:
                location = loc_match.group(1).strip()
            return {"type": "weather", "location": location}

        # News keywords
        news_words = ['news', 'latest', 'headlines', 'current events', 'happening',
                      'today\'s news', 'breaking']
        if any(w in msg for w in news_words):
            # Extract topic
            topic = ""
            topic_match = re.search(r'(?:news|headlines|updates)\s+(?:about|on|regarding)\s+(.+?)(?:\?|$|\.)', msg)
            if topic_match:
                topic = topic_match.group(1).strip()
            return {"type": "news", "query": topic}

        # YouTube keywords
        youtube_words = ['play', 'youtube', 'song', 'video']
        if any(w in msg for w in youtube_words) and 'play' in msg:
            # Extract query
            query = msg.replace('play', '').replace('on youtube', '').strip()
            return {"type": "action", "action": "play_youtube", "query": query}

        # WhatsApp / Message keywords
        # Trigger on by: "whatsapp" OR ("send" + "message/msg") OR ("message to")
        is_whatsapp = 'whatsapp' in msg
        is_send_msg = 'send' in msg and ('message' in msg or 'msg' in msg)
        is_msg_to = 'message to' in msg
        
        if is_whatsapp or is_send_msg or is_msg_to:
            # 1. Extract phone number
            phone_match = re.search(r'(\+?\d[\d\s-]{9,}\d)', msg)
            phone = ""
            if phone_match:
                raw_phone = phone_match.group(1)
                phone = re.sub(r'[\s-]', '', raw_phone)
                if not phone.startswith('+'):
                    if len(phone) == 10:
                        phone = "+91" + phone
                    else:
                        phone = "+" + phone
            
            # 2. Extract recipient name if phone not found
            # Exclude common verbs that might follow "to"
            excluded_names = ['me', 'us', 'him', 'her', 'them', 'someone', 'send', 'message', 'whatsapp']
            recipient_name = ""
            if not phone:
                # Look for "to [Name]"
                # e.g., "send message to Harsh" -> Harsh
                to_matches = re.finditer(r'\bto\s+([a-zA-Z]+)(?:\s|$)', msg, re.IGNORECASE)
                for match in to_matches:
                    candidate = match.group(1)
                    if candidate.lower() not in excluded_names:
                        recipient_name = candidate
                        break

            # 3. Extract Message Content
            # Strategy: Look for "saying", "that says", "telling" - everything after is the message
            # Added "tell him", "tell her", "tell", "that" to catch more patterns
            splitters = [
                'saying', 'that says', 'is saying', 
                'telling him', 'telling her', 'telling them', 'telling',
                'tell him', 'tell her', 'tell them', 'tell',
                'that'
            ]
            message_content = ""
            
            # Check for splitters
            for splitter in splitters:
                pattern = r'\b' + re.escape(splitter) + r'\b'
                split_match = re.search(pattern, msg, re.IGNORECASE)
                if split_match:
                    # Found a splitter! Everything after is the message
                    message_content = msg[split_match.end():].strip()
                    break
            
            # If no splitter found, fall back to cleanup
            if not message_content:
                message_content = msg
                
                # Remove triggers
                message_content = re.sub(r'\bwhatsapp\b', '', message_content, flags=re.IGNORECASE)
                
                if phone_match:
                    message_content = message_content.replace(phone_match.group(1), '')
                
                if recipient_name:
                    message_content = re.sub(r'\bto\s+' + re.escape(recipient_name), '', message_content, flags=re.IGNORECASE)
                
                # Remove "send message to", "msg to"
                message_content = re.sub(r'\bsend\b|\bmessage\b|\bmsg\b', '', message_content, flags=re.IGNORECASE)
                
                # Remove "to" if it's just hanging
                message_content = re.sub(r'\bto\b', '', message_content, flags=re.IGNORECASE)
                
                # Remove polite prefixes
                prefixes = ['can you', 'could you', 'please', 'i want', 'i need', 'and']
                for prefix in prefixes:
                     message_content = re.sub(r'\b' + prefix + r'\b', '', message_content, flags=re.IGNORECASE)

            # Final cleanup
            message_content = re.sub(r'\s+', ' ', message_content).strip()
            message_content = re.sub(r'^[:\-,]+', '', message_content).strip()
            
            # Remove leading "that", "a", "an", "and" if they remain
            # Only remove if it's at the start and followed by space or end of string
            message_content = re.sub(r'^(that|a|an|and|to)\s+', '', message_content, flags=re.IGNORECASE).strip()
            
            return {
                "type": "action", 
                "action": "whatsapp_message", 
                "phone": phone, 
                "recipient_name": recipient_name,
                "message": message_content
            }

        # Handwriting keywords
        handwriting_words = ['handwriting', 'write in hand', 'convert to hand']
        if any(w in msg for w in handwriting_words):
            text = msg.replace('convert to handwriting', '').strip()
            return {"type": "action", "action": "handwriting", "text": text}

        # Time/date keywords
        time_words = ['what time', 'current time', 'date today', 'what day', 'today\'s date']
        if any(w in msg for w in time_words):
            return {"type": "time"}

        return {"type": "none"}


# Global instance
web_services = WebServices()
