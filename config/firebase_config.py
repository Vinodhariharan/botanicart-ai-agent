import firebase_admin
from firebase_admin import credentials, firestore
import os
import json
from typing import Optional

class FirebaseConfig:
    _db: Optional[firestore.Client] = None
    
    @classmethod
    def initialize_firebase(cls):
        if not firebase_admin._apps:
            # Create credentials from environment variables
            firebase_credentials = {
                "type": "service_account",
                "project_id": os.getenv("FIREBASE_PROJECT_ID"),
                "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID"),
                "private_key": os.getenv("FIREBASE_PRIVATE_KEY").replace('\\n', '\n'),
                "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
                "client_id": os.getenv("FIREBASE_CLIENT_ID"),
                "auth_uri": os.getenv("FIREBASE_AUTH_URI"),
                "token_uri": os.getenv("FIREBASE_TOKEN_URI"),
            }
            
            cred = credentials.Certificate(firebase_credentials)
            firebase_admin.initialize_app(cred)
        
        cls._db = firestore.client()
        return cls._db
    
    @classmethod
    def get_db(cls) -> firestore.Client:
        if cls._db is None:
            return cls.initialize_firebase()
        return cls._db