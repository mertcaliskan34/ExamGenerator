from fastapi import FastAPI, APIRouter, HTTPException, Depends, File, UploadFile, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional, Literal
import uuid
from datetime import datetime, timezone, timedelta
import jwt
from passlib.context import CryptContext
import tempfile
from PyPDF2 import PdfReader
import google.generativeai as genai

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Security
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = os.environ.get("SECRET_KEY", "exam-generator-secret-key-2025")
ALGORITHM = "HS256"
security = HTTPBearer()

# Google AI Key
GOOGLE_AI_KEY = os.environ.get("GOOGLE_AI_KEY")

# Create the main app
app = FastAPI()
api_router = APIRouter(prefix="/api")

# Models
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: EmailStr
    full_name: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Question(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    question_text: str
    question_type: Literal["multiple_choice", "true_false", "fill_blank", "open_ended"]
    options: Optional[List[str]] = None
    correct_answer: str
    explanation: Optional[str] = None

class ExamCreate(BaseModel):
    exam_type: Literal["multiple_choice", "true_false", "fill_blank", "open_ended", "mixed"]
    difficulty: Literal["easy", "medium", "hard"]
    num_questions: int = Field(ge=5, le=50)

class Exam(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    title: str
    exam_type: str
    difficulty: str
    questions: List[Question]
    pdf_name: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ExamAnswer(BaseModel):
    question_id: str
    user_answer: str

class ExamSubmission(BaseModel):
    exam_id: str
    answers: List[ExamAnswer]

class ExamResult(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    exam_id: str
    user_id: str
    score: float
    total_questions: int
    correct_answers: int
    answers: List[ExamAnswer]
    feedback: List[dict]
    submitted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Helper Functions
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: timedelta = timedelta(days=7)):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid authentication")
        user = await db.users.find_one({"id": user_id}, {"_id": 0})
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text from PDF file"""
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    return text

async def generate_exam_with_ai(pdf_text: str, exam_type: str, difficulty: str, num_questions: int) -> List[Question]:
    """Generate exam questions using AI"""
    try:
        # Configure Google AI
        genai.configure(api_key=GOOGLE_AI_KEY)
        
        # Create prompt based on exam type
        type_instruction = {
            "multiple_choice": "Create multiple choice questions with 4 options (A, B, C, D). Provide the correct answer letter.",
            "true_false": "Create true/false questions. Answer should be 'True' or 'False'.",
            "fill_blank": "Create fill-in-the-blank questions. Use '___' to indicate the blank. Provide the correct answer.",
            "open_ended": "Create open-ended questions that require detailed answers. Provide a sample correct answer.",
            "mixed": "Create a mix of multiple choice, true/false, fill-in-the-blank, and open-ended questions."
        }
        
        prompt = f"""You are an expert exam creator. Generate high-quality exam questions based on the provided content.

Based on the following content, create {num_questions} {difficulty} difficulty exam questions.

{type_instruction[exam_type]}

Content:
{pdf_text[:4000]}

IMPORTANT: Return ONLY a valid JSON array with this exact structure:
[
  {{
    "question_text": "The question text here",
    "question_type": "multiple_choice" or "true_false" or "fill_blank" or "open_ended",
    "options": ["A. Option 1", "B. Option 2", "C. Option 3", "D. Option 4"] (only for multiple_choice),
    "correct_answer": "The correct answer",
    "explanation": "Brief explanation of the answer"
  }}
]

Do not include any text before or after the JSON array."""
        
        # Generate content using Gemini
        # First, let's try to list available models for debugging
        try:
            models = genai.list_models()
            logging.info(f"Available models: {[m.name for m in models]}")
        except Exception as e:
            logging.warning(f"Could not list models: {e}")
        
        # Try different model names (using the available models from the logs)
        model_names_to_try = ['gemini-2.5-pro', 'gemini-2.5-flash', 'gemini-2.0-flash', 'gemini-pro-latest']
        model = None
        
        for model_name in model_names_to_try:
            try:
                model = genai.GenerativeModel(model_name)
                logging.info(f"Successfully created model: {model_name}")
                break
            except Exception as e:
                logging.warning(f"Failed to create model {model_name}: {e}")
                continue
        
        if not model:
            raise HTTPException(status_code=500, detail="No available Gemini models found")
        
        response = model.generate_content(prompt)
        response_text = response.text.strip()
        
        # Parse response
        import json
        # Remove markdown code blocks if present
        if response_text.startswith("```"):
            response_text = response_text.split("\n", 1)[1]
            response_text = response_text.rsplit("```", 1)[0]
        
        questions_data = json.loads(response_text)
        
        # Convert to Question objects
        questions = []
        for q_data in questions_data:
            question = Question(
                question_text=q_data["question_text"],
                question_type=q_data["question_type"],
                options=q_data.get("options"),
                correct_answer=q_data["correct_answer"],
                explanation=q_data.get("explanation")
            )
            questions.append(question)
        
        return questions
    except Exception as e:
        logging.error(f"Error generating exam: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate exam: {str(e)}")

# Routes
@api_router.post("/auth/register", response_model=dict)
async def register(user_data: UserCreate):
    # Check if user exists
    existing_user = await db.users.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    user = User(
        email=user_data.email,
        full_name=user_data.full_name
    )
    
    user_doc = user.model_dump()
    user_doc["password_hash"] = hash_password(user_data.password)
    user_doc["created_at"] = user_doc["created_at"].isoformat()
    
    await db.users.insert_one(user_doc)
    
    # Create token
    token = create_access_token({"sub": user.id})
    
    return {
        "token": token,
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name
        }
    }

@api_router.post("/auth/login", response_model=dict)
async def login(credentials: UserLogin):
    user = await db.users.find_one({"email": credentials.email}, {"_id": 0})
    if not user or not verify_password(credentials.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    token = create_access_token({"sub": user["id"]})
    
    return {
        "token": token,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "full_name": user["full_name"]
        }
    }

@api_router.post("/exams/create", response_model=Exam)
async def create_exam(
    pdf: UploadFile = File(...),
    exam_type: str = "mixed",
    difficulty: str = "medium",
    num_questions: int = 10,
    current_user: dict = Depends(get_current_user)
):
    # Validate PDF
    if not pdf.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    # Save PDF temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        content = await pdf.read()
        tmp_file.write(content)
        tmp_path = tmp_file.name
    
    try:
        # Extract text from PDF
        pdf_text = extract_text_from_pdf(tmp_path)
        
        if not pdf_text.strip():
            raise HTTPException(status_code=400, detail="Could not extract text from PDF")
        
        # Generate exam questions
        questions = await generate_exam_with_ai(pdf_text, exam_type, difficulty, num_questions)
        
        # Create exam
        exam = Exam(
            user_id=current_user["id"],
            title=f"Exam from {pdf.filename}",
            exam_type=exam_type,
            difficulty=difficulty,
            questions=questions,
            pdf_name=pdf.filename
        )
        
        exam_doc = exam.model_dump()
        exam_doc["created_at"] = exam_doc["created_at"].isoformat()
        exam_doc["questions"] = [q.model_dump() for q in questions]
        
        await db.exams.insert_one(exam_doc)
        
        return exam
    finally:
        # Clean up temporary file
        os.unlink(tmp_path)

@api_router.get("/exams", response_model=List[Exam])
async def get_exams(current_user: dict = Depends(get_current_user)):
    exams = await db.exams.find({"user_id": current_user["id"]}, {"_id": 0}).to_list(1000)
    
    for exam in exams:
        if isinstance(exam["created_at"], str):
            exam["created_at"] = datetime.fromisoformat(exam["created_at"])
    
    return exams

@api_router.get("/exams/{exam_id}", response_model=Exam)
async def get_exam(exam_id: str, current_user: dict = Depends(get_current_user)):
    exam = await db.exams.find_one({"id": exam_id, "user_id": current_user["id"]}, {"_id": 0})
    
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    
    if isinstance(exam["created_at"], str):
        exam["created_at"] = datetime.fromisoformat(exam["created_at"])
    
    return exam

@api_router.post("/exams/submit", response_model=ExamResult)
async def submit_exam(submission: ExamSubmission, current_user: dict = Depends(get_current_user)):
    # Get exam
    exam = await db.exams.find_one({"id": submission.exam_id, "user_id": current_user["id"]}, {"_id": 0})
    
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    
    # Evaluate answers
    correct_count = 0
    feedback = []
    
    for answer in submission.answers:
        question = next((q for q in exam["questions"] if q["id"] == answer.question_id), None)
        if question:
            is_correct = answer.user_answer.strip().lower() == question["correct_answer"].strip().lower()
            if is_correct:
                correct_count += 1
            
            feedback.append({
                "question_id": answer.question_id,
                "is_correct": is_correct,
                "correct_answer": question["correct_answer"],
                "user_answer": answer.user_answer,
                "explanation": question.get("explanation", "")
            })
    
    total_questions = len(exam["questions"])
    score = (correct_count / total_questions) * 100 if total_questions > 0 else 0
    
    # Save result
    result = ExamResult(
        exam_id=submission.exam_id,
        user_id=current_user["id"],
        score=score,
        total_questions=total_questions,
        correct_answers=correct_count,
        answers=submission.answers,
        feedback=feedback
    )
    
    result_doc = result.model_dump()
    result_doc["submitted_at"] = result_doc["submitted_at"].isoformat()
    result_doc["answers"] = [a.model_dump() for a in submission.answers]
    
    await db.exam_results.insert_one(result_doc)
    
    return result

@api_router.get("/results", response_model=List[ExamResult])
async def get_results(current_user: dict = Depends(get_current_user)):
    results = await db.exam_results.find({"user_id": current_user["id"]}, {"_id": 0}).to_list(1000)
    
    for result in results:
        if isinstance(result["submitted_at"], str):
            result["submitted_at"] = datetime.fromisoformat(result["submitted_at"])
    
    return results

@api_router.get("/results/{result_id}", response_model=ExamResult)
async def get_result(result_id: str, current_user: dict = Depends(get_current_user)):
    result = await db.exam_results.find_one({"id": result_id, "user_id": current_user["id"]}, {"_id": 0})
    
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")
    
    if isinstance(result["submitted_at"], str):
        result["submitted_at"] = datetime.fromisoformat(result["submitted_at"])
    
    return result

# Include router
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()