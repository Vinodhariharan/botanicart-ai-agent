from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import create_react_agent, AgentExecutor
from langchain.tools import Tool
from langchain.prompts import PromptTemplate
from tools.firestore_tools import FirestoreProductTool, FirestoreCareGuideTool, FirestoreCategoryTool
import json
import re
from typing import Dict, List, Any

class PlantRecommendationAgent:
    def __init__(self, gemini_api_key: str):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            google_api_key=gemini_api_key,
            temperature=0.2,  # Reduced for more consistent results
            max_tokens=1200   # Increased for more comprehensive responses
        )
        
        # Initialize tools
        self.product_tool = FirestoreProductTool()
        self.care_tool = FirestoreCareGuideTool()
        self.category_tool = FirestoreCategoryTool()
        
        self.tools = [
            Tool(
                name="search_products",
                description="Search for plant products. ALWAYS use this tool first for plant recommendations. Use broad keywords initially, then narrow if needed. Examples: 'low light plants', 'beginner plants', 'pet safe succulents', 'under $30'.",
                func=self.product_tool.search_products
            ),
            Tool(
                name="get_care_guides",
                description="Get plant care instructions. Use after finding products or when asked about plant care. Include plant names or care topics.",
                func=self.care_tool.get_care_guides
            ),
            Tool(
                name="get_categories",
                description="Get available product categories. Use when customer wants to explore options or when no specific products found.",
                func=self.category_tool.get_categories
            )
        ]
        
        self.prompt = PromptTemplate.from_template("""
You are an expert plant consultant helping customers find plants and care guidance. Your goal is to ALWAYS provide helpful recommendations by actively using your tools.

CRITICAL INSTRUCTIONS:
1. ALWAYS use search_products tool first when customers ask for plant recommendations
2. If initial search yields few results, try broader search terms
3. Use multiple searches with different keywords if needed
4. Only ask clarifying questions AFTER attempting to find relevant products
5. Provide specific product recommendations with prices and care tips
6. Include care guidance when relevant

Your tools provide real-time data from our inventory:
- search_products: Find plants matching customer needs (use broad terms first)
- get_care_guides: Get detailed care instructions 
- get_categories: Browse available plant types

SEARCH STRATEGY:
- Start with broad terms: "indoor plants", "low light", "beginner"
- Then try specific terms: "succulents", "air purifying", "pet safe"
- Include budget if mentioned: "under $50", "budget plants"
- Try multiple searches to find the best matches

RESPONSE FORMAT:
- Lead with product recommendations when found
- Include prices, care level, and key features
- Mention pet safety when relevant
- Provide care tips or guide links
- Ask follow-up questions to refine recommendations

You have access to these tools: {tools}

Use this format:

Question: the input question you must answer
Thought: I need to search for products that match this customer's needs
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action

... (repeat Thought/Action/Action Input/Observation as needed)

Thought: I now have enough information to provide helpful recommendations
Final Answer: [Provide specific product recommendations with details, prices, and care tips. If few products found, suggest alternatives and ask clarifying questions.]

Begin!

Customer message: {input}
{agent_scratchpad}
""")
        
        self.agent = create_react_agent(self.llm, self.tools, self.prompt)
        self.executor = AgentExecutor(
            agent=self.agent, 
            tools=self.tools, 
            verbose=True,
            max_iterations=6,  # Increased to allow more tool usage
            handle_parsing_errors=True,
            return_intermediate_steps=True
        )
    
    def get_recommendation(self, user_message: str, user_id: str = None) -> Dict[str, Any]:
        """Process user message and return recommendations"""
        try:
            # Execute agent with enhanced error handling
            response = self.executor.invoke({
                "input": user_message
            })
            
            # Parse the response to extract structured data
            agent_response = response.get('output', '')
            
            # Extract products and care guides from the agent's tool usage
            products = self._extract_products_from_agent_response(response)
            care_guides = self._extract_care_guides_from_agent_response(response)
            
            # If no products found but agent didn't search, try a fallback search
            if not products and not self._agent_searched_products(response):
                products = self._fallback_product_search(user_message)
            
            # Understand what the user was looking for
            query_analysis = self._analyze_user_query(user_message)
            
            # Generate suggested actions
            suggested_actions = self._generate_suggested_actions(user_message, products, care_guides, agent_response)
            
            # Calculate confidence score (more lenient)
            confidence = self._calculate_confidence(user_message, products, care_guides, agent_response)
            
            return {
                "response": agent_response,
                "product_recommendations": products,
                "care_guides": care_guides,
                "suggested_actions": suggested_actions,
                "confidence_score": confidence,
                "query_understood": query_analysis
            }
            
        except Exception as e:
            print(f"Agent execution error: {str(e)}")
            # Fallback: try direct product search
            fallback_products = self._fallback_product_search(user_message)
            
            return {
                "response": "I found some plants that might interest you! Let me know if you'd like more specific recommendations or have questions about plant care.",
                "product_recommendations": fallback_products,
                "care_guides": [],
                "suggested_actions": self._generate_fallback_actions(user_message),
                "confidence_score": 0.6 if fallback_products else 0.3,
                "query_understood": self._analyze_user_query(user_message)
            }
    
    def _agent_searched_products(self, response: Dict) -> bool:
        """Check if the agent actually used the search_products tool"""
        try:
            intermediate_steps = response.get('intermediate_steps', [])
            for step in intermediate_steps:
                if len(step) >= 2:
                    action = step[0]
                    if hasattr(action, 'tool') and action.tool == 'search_products':
                        return True
            return False
        except:
            return False
    
    def _fallback_product_search(self, user_message: str) -> List[Dict[str, Any]]:
        """Perform a fallback product search if agent didn't search"""
        try:
            # Try a broad search based on common keywords
            search_terms = []
            query_lower = user_message.lower()
            
            if any(word in query_lower for word in ['beginner', 'easy', 'simple']):
                search_terms.append('beginner plants')
            elif any(word in query_lower for word in ['low light', 'dark', 'shade']):
                search_terms.append('low light plants')
            elif any(word in query_lower for word in ['succulent', 'cactus']):
                search_terms.append('succulents')
            elif any(word in query_lower for word in ['pet', 'cat', 'dog', 'safe']):
                search_terms.append('pet safe plants')
            else:
                search_terms.append('indoor plants')
            
            # Try each search term
            for term in search_terms:
                try:
                    result_str = self.product_tool.search_products(term)
                    products = json.loads(result_str)
                    if isinstance(products, list) and products:
                        return products[:5]  # Return first 5 results
                except:
                    continue
            
            return []
        except Exception as e:
            print(f"Fallback search error: {e}")
            return []
    
    def _generate_fallback_actions(self, user_message: str) -> List[str]:
        """Generate fallback suggested actions"""
        query_lower = user_message.lower()
        actions = []
        
        if 'care' not in query_lower:
            actions.append("Show me plant care guides")
        if 'beginner' not in query_lower:
            actions.append("Find beginner-friendly plants")
        if 'pet' not in query_lower:
            actions.append("Show pet-safe options")
        if 'low light' not in query_lower:
            actions.append("Find plants for low light")
        
        return actions[:3]
   
    def _extract_products_from_agent_response(self, response: Dict) -> List[Dict[str, Any]]:
        """Extract product information from the latest relevant agent tool usage."""
        try:
            intermediate_steps = response.get('intermediate_steps', [])
            
            # Look for the most recent successful product search
            for step in reversed(intermediate_steps): 
                if len(step) >= 2:
                    action, observation_str = step[0], step[1]
                    if hasattr(action, 'tool') and action.tool == 'search_products':
                        try:
                            products_data = json.loads(observation_str)
                            if isinstance(products_data, list) and products_data: 
                                return products_data
                        except json.JSONDecodeError:
                            continue
                        except Exception:
                            continue
            
            return []
            
        except Exception as e:
            print(f"Error in _extract_products_from_agent_response: {e}")
            return []
    
    def _extract_care_guides_from_agent_response(self, response: Dict) -> List[Dict[str, Any]]:
        """Extract care guide information from agent tool usage"""
        try:
            intermediate_steps = response.get('intermediate_steps', [])
            
            for step in reversed(intermediate_steps):
                if len(step) >= 2:
                    action, observation = step[0], step[1]
                    if hasattr(action, 'tool') and action.tool == 'get_care_guides':
                        try:
                            care_guides_data = json.loads(observation)
                            if isinstance(care_guides_data, list) and care_guides_data:
                                return care_guides_data
                        except json.JSONDecodeError:
                            continue
            
            return []
            
        except Exception as e:
            print(f"Error extracting care guides: {e}")
            return []

    def _analyze_user_query(self, user_message: str) -> Dict[str, Any]:
        """Analyze the user's query to understand intent and extract key information."""
        query_lower = user_message.lower()
        analysis = {
            "original_query": user_message,
            "intent": "unknown",
            "keywords": [],
            "entities": {},
            "urgency": "normal"
        }

        # Intent detection
        if any(phrase in query_lower for phrase in ["how to care", "care guide", "problem with", "help with", "dying", "yellow leaves"]):
            analysis["intent"] = "care_guidance"
            analysis["urgency"] = "high" if any(word in query_lower for word in ["dying", "help", "problem"]) else "normal"
        elif any(phrase in query_lower for phrase in ["looking for", "recommend", "buy", "find plant", "suggest", "need a plant", "want a plant"]):
            analysis["intent"] = "product_recommendation"
        elif any(phrase in query_lower for phrase in ["category", "categories", "types of plants", "what plants"]):
            analysis["intent"] = "category_inquiry"
        else:
            # Try to infer from context
            if any(word in query_lower for word in ["plant", "succulent", "flower", "tree"]):
                analysis["intent"] = "product_recommendation"

        # Extract keywords
        common_words = {"a", "an", "the", "is", "are", "for", "to", "of", "i", "me", "my", "need", "want", "can", "you", "help"}
        analysis["keywords"] = [word for word in re.findall(r'\b\w+\b', query_lower) if word not in common_words and len(word) > 2]

        # Extract entities using product tool parser
        try:
            extracted_filters = self.product_tool._parse_query(user_message)
            if extracted_filters:
                analysis["entities"] = extracted_filters
                if analysis["intent"] == "unknown":
                    analysis["intent"] = "product_recommendation"
        except:
            pass

        return analysis

    def _generate_suggested_actions(self, user_message: str, products: List[Dict], care_guides: List[Dict], agent_response: str) -> List[str]:
        """Generate relevant suggested actions based on context"""
        suggestions = []
        query_lower = user_message.lower()
        response_lower = agent_response.lower()

        # Check if agent asked clarifying questions
        clarification_indicators = [
            "tell me more", "could you tell me", "what's your experience", 
            "what's your budget", "any pets", "how much sun", "where will"
        ]
        
        asked_for_clarification = any(indicator in response_lower for indicator in clarification_indicators)

        if asked_for_clarification:
            # Provide specific answers to common clarifying questions
            if "experience" in response_lower:
                suggestions.extend(["I'm a beginner", "I'm experienced with plants"])
            if "budget" in response_lower:
                suggestions.extend(["Under $30", "Under $50", "$50-100"])
            if "pets" in response_lower:
                suggestions.extend(["Yes, I have pets", "No pets"])
            if "sun" in response_lower or "light" in response_lower:
                suggestions.extend(["Bright indirect light", "Low light area", "Direct sunlight"])
            if "where" in response_lower or "location" in response_lower:
                suggestions.extend(["Indoor living room", "Office desk", "Bedroom"])
        
        elif products:
            # Product-specific suggestions
            if len(products) == 1:
                product_title = products[0].get('title', 'this plant')
                suggestions.append(f"Care guide for {product_title}")
            
            # Add complementary searches
            if 'low light' not in query_lower:
                suggestions.append("Show low-light options")
            if 'pet safe' not in query_lower and 'pet' not in query_lower:
                suggestions.append("Find pet-safe plants")
            if not any(price_term in query_lower for price_term in ['$', 'budget', 'cheap', 'expensive']):
                suggestions.append("Show budget-friendly options")
            
            suggestions.append("Browse plant categories")
        
        elif care_guides:
            # Care guide specific suggestions
            suggestions.extend([
                "Find related plants to buy",
                "More care guides",
                "Common plant problems"
            ])
        
        else:
            # No results found - provide helpful alternatives
            suggestions.extend([
                "Show popular indoor plants",
                "Find beginner-friendly plants", 
                "Browse plant categories",
                "Plant care basics"
            ])

        # Remove duplicates and limit to 4
        final_suggestions = list(dict.fromkeys(suggestions))[:4]
        
        # Ensure we always have at least 2 suggestions
        if len(final_suggestions) < 2:
            default_suggestions = [
                "Show me indoor plants",
                "Plant care tips",
                "Browse categories"
            ]
            final_suggestions.extend([s for s in default_suggestions if s not in final_suggestions])
        
        return final_suggestions[:4]

    def _calculate_confidence(self, user_message: str, products: List[Dict], care_guides: List[Dict], agent_response: str) -> float:
        """Calculate confidence score - more lenient to show results even with lower confidence"""
        base_score = 0.4  # Start with a reasonable base
        
        # Boost for finding results
        if products:
            base_score += 0.3
            # Additional boost for multiple relevant results
            if len(products) > 1:
                base_score += 0.1
            # Boost for products with good match scores
            good_matches = [p for p in products if p.get('match_score', 0) > 0.7]
            if good_matches:
                base_score += 0.1
        
        if care_guides:
            base_score += 0.2
            if len(care_guides) > 1:
                base_score += 0.1
        
        # Boost for specific queries
        query_lower = user_message.lower()
        specific_terms = ['beginner', 'low light', 'pet safe', 'succulent', 'indoor', 'office', 'bedroom']
        specific_matches = sum(1 for term in specific_terms if term in query_lower)
        base_score += min(specific_matches * 0.05, 0.15)
        
        # Boost if agent provided helpful response
        response_lower = agent_response.lower()
        helpful_indicators = ['recommend', 'suggest', 'perfect', 'great choice', 'here are']
        if any(indicator in response_lower for indicator in helpful_indicators):
            base_score += 0.1
        
        # Penalize only if truly no helpful information provided
        if not products and not care_guides and len(agent_response) < 50:
            base_score -= 0.2
        
        # Ensure minimum confidence when results are found
        if products or care_guides:
            base_score = max(base_score, 0.5)
        
        return min(max(base_score, 0.0), 1.0)

# Example usage and testing code remains the same
if __name__ == '__main__':
    import os
    from dotenv import load_dotenv
    load_dotenv(dotenv_path='../.env')
    
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    
    if not gemini_api_key:
        print("GEMINI_API_KEY not found in .env file.")
    else:
        # Mock Firebase setup (same as before)
        class MockFirestoreCollection:
            def where(self, *args, **kwargs): return self
            def limit(self, *args, **kwargs): return self
            def stream(self, *args, **kwargs): return []
            def to_dict(self): return {}

        class MockFirebaseConfig:
            _db = None
            @classmethod
            def initialize_firebase(cls):
                print("Mock Firebase Initialized")
                cls._db = cls
                return cls._db
            
            @classmethod
            def get_db(cls):
                if cls._db is None:
                    return cls.initialize_firebase()
                return cls._db
            
            def collection(self, name):
                print(f"Mock Firestore: Accessing collection {name}")
                if name == 'products':
                    class MockProductQuery:
                        def where(self, *args, **kwargs): return self
                        def limit(self, *args, **kwargs): return self
                        def stream(self):
                            class MockDoc:
                                def __init__(self, data): self._data = data
                                def to_dict(self): return self._data
                            
                            return [
                                MockDoc({
                                    'title': 'Peace Lily', 'price': 25.0, 'description': 'Great air purifier',
                                    'category': 'Air Purifying', 'subCategory': 'Floor Plants', 'type': 'Indoor Plant',
                                    'details': {'sunlight': 'indirect', 'maintenance': 'low', 'toxicity': 'toxic to pets'},
                                    'stock': {'availability': True, 'quantity': 10}, 'imageSrc':'peace_lily.jpg', 'link':'/peace-lily',
                                    'match_score': 0.85
                                }),
                                MockDoc({
                                    'title': 'Snake Plant', 'price': 30.0, 'description': 'Very hardy plant',
                                    'category': 'Air Purifying', 'subCategory': 'Desktop Plants', 'type': 'Indoor Plant',
                                    'details': {'sunlight': 'low to bright indirect', 'maintenance': 'low', 'toxicity': 'mildly toxic'},
                                    'stock': {'availability': True, 'quantity': 5}, 'imageSrc':'snake_plant.jpg', 'link':'/snake-plant',
                                    'match_score': 0.90
                                })
                            ]
                    return MockProductQuery()
                elif name == 'care_guides':
                    class MockCareGuideQuery:
                        def where(self, *args, **kwargs): return self
                        def limit(self, *args, **kwargs): return self
                        def stream(self):
                            class MockDoc:
                                def __init__(self, data): self._data = data
                                def to_dict(self): return self._data
                            return [
                                MockDoc({
                                    'title': 'Basic Indoor Plant Care', 'description': 'Easy tips for beginners.',
                                    'category': 'General', 'difficulty': 'Easy', 'quickTips': ['Water regularly'],
                                    'relevanceScore': 4.5
                                })
                            ]
                    return MockCareGuideQuery()
                return MockFirestoreCollection()

        import tools.firestore_tools as ft
        original_firebase_config = ft.FirebaseConfig
        ft.FirebaseConfig = MockFirebaseConfig
        
        agent = PlantRecommendationAgent(gemini_api_key=gemini_api_key)
        
        ft.FirebaseConfig = original_firebase_config

        test_queries = [
            "Recommend a low maintenance plant for my office under $30",
            "How to care for a Fiddle Leaf Fig?",
            "Show me pet-safe plants",
            "What are some good beginner friendly succulents?",
            "I'm looking for a plant for a sunny spot."
        ]
        
        for query in test_queries:
            print(f"\n--- Testing query: {query} ---")
            recommendation = agent.get_recommendation(query)
            print(json.dumps(recommendation, indent=2))
            print("---------------------------\n")