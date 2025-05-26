# tools/firestore_tools.py

from langchain.tools import Tool
from config.firebase_config import FirebaseConfig
import json
from typing import List, Dict, Any
import re

class FirestoreProductTool:
    def __init__(self):
        self.db = FirebaseConfig.get_db()
    
    def search_products(self, query: str) -> str:
        """
        Search products based on customer needs, experience level, space conditions
        Query format: "beginner plants under $50 for low light"
        """
        try:
            products_ref = self.db.collection('products')
            filters = self._parse_query(query)
            
            query_ref = products_ref.where('stock.availability', '==', True)
            
            if filters.get('category'):
                query_ref = query_ref.where('category', '==', filters['category'])
            
            if filters.get('sub_category'):
                query_ref = query_ref.where('subCategory', '==', filters['sub_category'])
            
            if filters.get('type'):
                query_ref = query_ref.where('type', '==', filters['type'])
            
            docs = query_ref.limit(50).stream()
            
            products = []
            for doc in docs:
                data = doc.to_dict()
                
                if filters.get('price_max') and data.get('price', 0) > filters['price_max']:
                    continue
                
                if filters.get('price_min') and data.get('price', 0) < filters['price_min']:
                    continue
                
                maintenance = data.get('details', {}).get('maintenance', '').lower()
                if filters.get('maintenance_level'):
                    if filters['maintenance_level'] == 'low' and 'low' not in maintenance:
                        continue
                    elif filters['maintenance_level'] == 'high' and 'high' not in maintenance:
                        continue
                
                sunlight = data.get('details', {}).get('sunlight', '').lower()
                if filters.get('sunlight') and filters['sunlight'] not in sunlight:
                    continue
                
                if filters.get('pet_safe'):
                    toxicity = data.get('details', {}).get('toxicity', '').lower()
                    if 'toxic' in toxicity or 'poisonous' in toxicity:
                        continue
                
                product = {
                    'id': doc.id,  # <--- ADDED PRODUCT ID (FIRESTORE DOCUMENT ID)
                    'title': data.get('title', ''),
                    'imageSrc': data.get('imageSrc', ''),
                    'price': data.get('price', 0),
                    'description': data.get('description', ''),
                    'link': data.get('link', ''),
                    'category': data.get('category', ''),
                    'subCategory': data.get('subCategory', ''),
                    'type': data.get('type', ''),
                    'details': {
                        'scientificName': data.get('details', {}).get('scientificName', ''),
                        'sunlight': data.get('details', {}).get('sunlight', ''),
                        'watering': data.get('details', {}).get('watering', ''),
                        'growthRate': data.get('details', {}).get('growthRate', ''),
                        'maintenance': data.get('details', {}).get('maintenance', ''),
                        'bloomSeason': data.get('details', {}).get('bloomSeason', ''),
                        'specialFeatures': data.get('details', {}).get('specialFeatures', ''),
                        'toxicity': data.get('details', {}).get('toxicity', ''),
                        'material': data.get('details', {}).get('material', ''),
                        'drainageHoles': data.get('details', {}).get('drainageHoles', False),
                        'size': data.get('details', {}).get('size', ''),
                        'color': data.get('details', {}).get('color', ''),
                        'useCase': data.get('details', {}).get('useCase', '')
                    },
                    'stock': {
                        'availability': data.get('stock', {}).get('availability', True),
                        'quantity': data.get('stock', {}).get('quantity', 0)
                    },
                    'match_score': self._calculate_match_score(data, filters)
                }
                
                products.append(product)
            
            products.sort(key=lambda x: x['match_score'], reverse=True)
            products = products[:8]
            
            return json.dumps(products, indent=2)
            
        except Exception as e:
            return f"Error searching products: {str(e)}"

    # ... (rest of FirestoreProductTool: _parse_query, _calculate_match_score) ...
    def _parse_query(self, query: str) -> Dict[str, Any]:
        """Parse natural language query into filters based on product structure"""
        filters = {}
        query_lower = query.lower()
        
        # Maintenance level detection (maps to details.maintenance)
        if any(word in query_lower for word in ['beginner', 'new', 'easy', 'simple', 'low maintenance']):
            filters['maintenance_level'] = 'low'
        elif any(word in query_lower for word in ['advanced', 'expert', 'difficult', 'high maintenance']):
            filters['maintenance_level'] = 'high'
        
        # Sunlight requirements (maps to details.sunlight)
        if any(word in query_lower for word in ['low light', 'shade', 'dark', 'indirect']):
            filters['sunlight'] = 'indirect'
        elif any(word in query_lower for word in ['bright', 'direct sun', 'sunny', 'full sun']):
            filters['sunlight'] = 'direct'
        elif any(word in query_lower for word in ['medium light', 'partial']):
            filters['sunlight'] = 'partial'
        
        # Category detection
        categories = {
            'succulent': 'Succulents & Cacti',
            'cactus': 'Succulents & Cacti',
            'flower': 'Flowering Plants',
            'flowering': 'Flowering Plants',
            'herb': 'Herbs & Edibles',
            'edible': 'Herbs & Edibles',
            'tree': 'Trees & Large Plants',
            'tropical': 'Tropical Plants',
            'air purifying': 'Air Purifying',
            'pot': 'Pots & Planters',
            'planter': 'Pots & Planters',
            'tool': 'Tools & Supplies',
            'fertilizer': 'Tools & Supplies'
        }
        
        for keyword, category in categories.items():
            if keyword in query_lower:
                filters['category'] = category
                break
        
        # Sub-category detection
        sub_categories = {
            'hanging': 'Hanging Plants',
            'trailing': 'Hanging Plants',
            'desk': 'Desktop Plants',
            'small': 'Desktop Plants',
            'tabletop': 'Desktop Plants',
            'floor': 'Floor Plants',
            'large': 'Floor Plants',
            'statement': 'Floor Plants'
        }
        
        for keyword, sub_category in sub_categories.items():
            if keyword in query_lower:
                filters['sub_category'] = sub_category
                break
        
        # Type detection
        types = {
            'indoor': 'Indoor Plant',
            'houseplant': 'Indoor Plant',
            'house plant': 'Indoor Plant',
            'outdoor': 'Outdoor Plant',
            'garden': 'Outdoor Plant',
            'ceramic': 'Ceramic Pot',
            'terracotta': 'Terracotta Pot',
            'fertilizer': 'Fertilizer',
            'plant food': 'Fertilizer',
            'tool': 'Garden Tool'
        }
        
        for keyword, plant_type in types.items():
            if keyword in query_lower:
                filters['type'] = plant_type
                break
        
        # Pet safety
        if any(word in query_lower for word in ['pet safe', 'cat safe', 'dog safe', 'non toxic']):
            filters['pet_safe'] = True
        
        # Price extraction
        price_patterns = [
            r'under \$(\d+)',
            r'below \$(\d+)',
            r'less than \$(\d+)',
            r'\$(\d+) or less',
            r'budget \$(\d+)'
        ]
        
        for pattern in price_patterns:
            price_match = re.search(pattern, query_lower)
            if price_match:
                filters['price_max'] = float(price_match.group(1))
                break
        
        # Price range extraction
        range_match = re.search(r'\$(\d+)[-\s]?to[-\s]?\$(\d+)', query_lower)
        if range_match:
            filters['price_min'] = float(range_match.group(1))
            filters['price_max'] = float(range_match.group(2))
        
        return filters
    
    def _calculate_match_score(self, product_data: Dict, filters: Dict) -> float:
        """Calculate how well a product matches the user's query"""
        score = 0.0
        max_score = 0.0
        
        # Maintenance level matching
        if filters.get('maintenance_level'):
            max_score += 3.0
            maintenance = product_data.get('details', {}).get('maintenance', '').lower()
            if filters['maintenance_level'] == 'low' and 'low' in maintenance:
                score += 3.0
            elif filters['maintenance_level'] == 'high' and 'high' in maintenance:
                score += 3.0
        
        # Sunlight matching
        if filters.get('sunlight'):
            max_score += 3.0
            sunlight = product_data.get('details', {}).get('sunlight', '').lower()
            if filters['sunlight'] in sunlight:
                score += 3.0
        
        # Category matching
        if filters.get('category'):
            max_score += 2.0
            if product_data.get('category', '').lower() == filters['category'].lower():
                score += 2.0
        
        # Type matching
        if filters.get('type'):
            max_score += 2.0
            if product_data.get('type', '').lower() == filters['type'].lower():
                score += 2.0
        
        # Pet safety
        if filters.get('pet_safe'):
            max_score += 1.0
            toxicity = product_data.get('details', {}).get('toxicity', '').lower()
            if 'non-toxic' in toxicity or 'safe' in toxicity:
                score += 1.0
        
        # Special features bonus
        special_features = product_data.get('details', {}).get('specialFeatures', '').lower()
        if special_features:
            if 'air purifying' in special_features:
                score += 0.5
            if 'low maintenance' in special_features:
                score += 0.5
        
        # Stock availability bonus
        stock = product_data.get('stock', {})
        if stock.get('availability') and stock.get('quantity', 0) > 0:
            score += 0.5
        
        return score / max(max_score, 1.0) if max_score > 0 else 0.5

# ... (FirestoreCareGuideTool and FirestoreCategoryTool remain the same) ...
class FirestoreCareGuideTool:
    def __init__(self):
        self.db = FirebaseConfig.get_db()
    
    def get_care_guides(self, plant_query: str) -> str:
        """
        Get plant care guidance based on plant type, category, or care issue
        """
        try:
            guides_ref = self.db.collection('care_guides')
            query_lower = plant_query.lower()
            
            matching_guides = []
            
            title_docs = guides_ref.where('title', '>=', plant_query).where('title', '<=', plant_query + '\uf8ff').limit(3).stream()
            for doc in title_docs: # Iterate to unpack generator
                matching_guides.append(doc)
            
            if not matching_guides:
                category_keywords = {
                    'tropical': 'Tropical Plants', 'succulent': 'Succulents & Cacti', 'cactus': 'Succulents & Cacti',
                    'flower': 'Flowering Plants', 'herb': 'Herbs & Edibles', 'monstera': 'Tropical Plants',
                    'snake plant': 'Air Purifying', 'pothos': 'Tropical Plants', 'spider plant': 'Air Purifying'
                }
                for keyword, category in category_keywords.items():
                    if keyword in query_lower:
                        category_docs = guides_ref.where('category', '==', category).limit(2).stream()
                        for doc in category_docs: # Iterate
                            matching_guides.append(doc)
                        break # Found category, no need to check others
            
            if not matching_guides:
                if any(word in query_lower for word in ['beginner', 'easy', 'simple']):
                    difficulty_docs = guides_ref.where('difficulty', '==', 'Easy').limit(3).stream()
                    for doc in difficulty_docs: # Iterate
                        matching_guides.append(doc)
                else:
                    general_docs = guides_ref.limit(3).stream()
                    for doc in general_docs: # Iterate
                        matching_guides.append(doc)
            
            guides = []
            # Deduplicate matching_guides by doc.id before processing
            unique_doc_ids = set()
            unique_matching_docs = []
            for doc in matching_guides:
                if doc.id not in unique_doc_ids:
                    unique_matching_docs.append(doc)
                    unique_doc_ids.add(doc.id)

            for doc in unique_matching_docs:
                if len(guides) >= 3:
                    break
                data = doc.to_dict()
                content_sections = [{'title': s.get('title', ''), 'text': s.get('text', ''), 'imageURL': s.get('imageURL', ''), 'imageCaption': s.get('imageCaption', '')} for s in data.get('content', [])]
                problems = [{'problem': p.get('problem', ''), 'solution': p.get('solution', '')} for p in data.get('commonProblems', [])]
                
                guide_data = {
                    'title': data.get('title', ''), 'description': data.get('description', ''),
                    'category': data.get('category', ''), 'difficulty': data.get('difficulty', ''),
                    'imageURL': data.get('imageURL', ''), 'publishDate': data.get('publishDate', ''),
                    'author': data.get('author', ''), 'quickTips': data.get('quickTips', []),
                    'wateringTips': data.get('wateringTips', ''), 'lightTips': data.get('lightTips', ''),
                    'temperatureTips': data.get('temperatureTips', ''), 'fertilizerTips': data.get('fertilizerTips', ''),
                    'content': content_sections, 'expertTip': data.get('expertTip', ''),
                    'expertName': data.get('expertName', ''), 'expertTitle': data.get('expertTitle', ''),
                    'commonProblems': problems, 'relevanceScore': self._calculate_relevance(data, plant_query)
                }
                guides.append(guide_data)
            
            guides.sort(key=lambda x: x['relevanceScore'], reverse=True)
            return json.dumps(guides, indent=2)
        except Exception as e:
            return f"Error getting care guides: {str(e)}"
    
    def _calculate_relevance(self, guide_data: Dict, query: str) -> float:
        score = 0.0
        query_lower = query.lower()
        if any(word in guide_data.get('title', '').lower() for word in query_lower.split()): score += 3.0
        if any(word in guide_data.get('category', '').lower() for word in query_lower.split()): score += 2.0
        if any(word in guide_data.get('description', '').lower() for word in query_lower.split()): score += 1.0
        if 'beginner' in query_lower and guide_data.get('difficulty') == 'Easy': score += 1.5
        elif 'advanced' in query_lower and guide_data.get('difficulty') == 'Advanced': score += 1.5
        return score

class FirestoreCategoryTool:
    def __init__(self):
        self.db = FirebaseConfig.get_db()
    
    def get_categories(self, query: str = "") -> str:
        try:
            categories_ref = self.db.collection('categories')
            docs = categories_ref.stream()
            categories = [{'id': doc.id, 'name': d.get('name', ''), 'description': d.get('description', ''), 'product_count': d.get('product_count', 0)} for doc in docs for d in [doc.to_dict()]]
            return json.dumps(categories, indent=2)
        except Exception as e:
            return f"Error getting categories: {str(e)}"