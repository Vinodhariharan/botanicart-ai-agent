# models/schemas.py

from pydantic import BaseModel
from typing import List, Optional, Dict, Any, Union
from datetime import datetime

class ChatRequest(BaseModel):
    message: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None

class ProductDetails(BaseModel):
    scientificName: Optional[str] = ""
    sunlight: Optional[str] = ""
    watering: Optional[str] = ""
    growthRate: Optional[str] = ""
    maintenance: Optional[str] = ""
    bloomSeason: Optional[str] = ""
    specialFeatures: Optional[str] = ""
    toxicity: Optional[str] = ""
    material: Optional[str] = ""
    drainageHoles: Optional[bool] = False
    size: Optional[str] = ""
    color: Optional[str] = ""
    useCase: Optional[str] = ""

class ProductStock(BaseModel):
    availability: bool = True
    quantity: int = 0

class ProductRecommendation(BaseModel):
    id: Optional[str] = None # <--- ADDED PRODUCT ID HERE
    title: str
    imageSrc: str
    price: float
    description: str
    link: str
    category: str
    subCategory: str
    type: str
    details: ProductDetails
    stock: ProductStock
    match_score: Optional[float] = 0.0

# ... (rest of your schemas.py file: ContentSection, CommonProblem, CareGuide, ChatResponse) ...
class ContentSection(BaseModel):
    title: str
    text: str
    imageURL: Optional[str] = ""
    imageCaption: Optional[str] = ""

class CommonProblem(BaseModel):
    problem: str
    solution: str

class CareGuide(BaseModel):
    title: str
    description: str
    category: str
    difficulty: str  # Easy, Moderate, Advanced
    imageURL: Optional[str] = ""
    publishDate: Optional[str] = ""
    author: Optional[str] = ""
    quickTips: List[str] = []
    wateringTips: Optional[str] = ""
    lightTips: Optional[str] = ""
    temperatureTips: Optional[str] = ""
    fertilizerTips: Optional[str] = ""
    content: List[ContentSection] = []
    expertTip: Optional[str] = ""
    expertName: Optional[str] = ""
    expertTitle: Optional[str] = ""
    commonProblems: List[CommonProblem] = []
    relevanceScore: Optional[float] = 0.0

class ChatResponse(BaseModel):
    response: str
    product_recommendations: List[ProductRecommendation] = []
    care_guides: List[CareGuide] = []
    suggested_actions: List[str] = []
    confidence_score: float = 0.0
    query_understood: Dict[str, Any] = {}