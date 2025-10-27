from fastapi import FastAPI, APIRouter, HTTPException, Depends, File, UploadFile, Form, status
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
from pdf2image import convert_from_path
from PIL import Image
import base64
import io

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
    question_type: Literal["multiple_choice", "true_false", "fill_blank", "open_ended", "image_based"]
    options: Optional[List[str]] = None
    correct_answer: str
    explanation: Optional[str] = None
    image_data: Optional[str] = None  # Base64 encoded image

class ExamCreate(BaseModel):
    exam_type: Literal["multiple_choice", "true_false", "fill_blank", "open_ended", "image_based", "mixed"]
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

def extract_images_from_pdf(pdf_path: str) -> List[str]:
    """Extract images from PDF and return as base64 strings"""
    try:
        # Try to convert PDF pages to images
        try:
            images = convert_from_path(pdf_path, dpi=150, fmt='jpeg')
        except Exception as e:
            logging.warning(f"pdf2image failed, trying alternative method: {str(e)}")
            # Alternative: Use PyPDF2 to extract images directly
            return extract_images_with_pypdf2(pdf_path)
        
        base64_images = []
        for img in images[:5]:  # Limit to first 5 pages to avoid too many images
            # Resize image if too large
            max_size = 1024
            if img.width > max_size or img.height > max_size:
                img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            
            # Convert to base64
            buffered = io.BytesIO()
            img.save(buffered, format="JPEG", quality=85)
            img_base64 = base64.b64encode(buffered.getvalue()).decode()
            base64_images.append(img_base64)
        
        return base64_images
    except Exception as e:
        logging.error(f"Error extracting images from PDF: {str(e)}")
        return []

def extract_images_with_pypdf2(pdf_path: str) -> List[str]:
    """Alternative method to extract images using PyPDF2"""
    try:
        from PyPDF2 import PdfReader
        import fitz  # PyMuPDF
        
        # Try PyMuPDF first
        try:
            doc = fitz.open(pdf_path)
            base64_images = []
            
            for page_num in range(min(5, len(doc))):  # First 5 pages
                page = doc[page_num]
                # Convert page to image
                mat = fitz.Matrix(2.0, 2.0)  # 2x zoom for better quality
                pix = page.get_pixmap(matrix=mat)
                img_data = pix.tobytes("jpeg")
                
                # Convert to PIL Image
                img = Image.open(io.BytesIO(img_data))
                
                # Resize if too large
                max_size = 1024
                if img.width > max_size or img.height > max_size:
                    img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                
                # Convert to base64
                buffered = io.BytesIO()
                img.save(buffered, format="JPEG", quality=85)
                img_base64 = base64.b64encode(buffered.getvalue()).decode()
                base64_images.append(img_base64)
            
            doc.close()
            return base64_images
            
        except ImportError:
            logging.warning("PyMuPDF not available, falling back to page images")
            # Fallback: Convert each page as image
            reader = PdfReader(pdf_path)
            base64_images = []
            
            for page_num in range(min(5, len(reader.pages))):
                # Create a simple page representation
                page = reader.pages[page_num]
                text = page.extract_text()
                
                # Create a simple text-based image representation
                if text.strip():
                    # Create a simple image with text content
                    img = Image.new('RGB', (800, 600), color='white')
                    # This is a simplified approach - in production you'd want proper text rendering
                    base64_images.append(create_text_image_base64(text[:500]))
            
            return base64_images
            
    except Exception as e:
        logging.error(f"Error with PyPDF2 image extraction: {str(e)}")
        return []

def create_text_image_base64(text: str) -> str:
    """Create a simple text-based image and return as base64"""
    try:
        # Create a simple image with text
        img = Image.new('RGB', (800, 600), color='white')
        # For now, return a placeholder
        buffered = io.BytesIO()
        img.save(buffered, format="JPEG", quality=85)
        return base64.b64encode(buffered.getvalue()).decode()
    except Exception as e:
        logging.error(f"Error creating text image: {str(e)}")
        return ""

async def generate_image_based_exam(pdf_path: str, difficulty: str, num_questions: int) -> List[Question]:
    """Generate image-based exam questions using AI with visual analysis"""
    try:
        # Extract images from PDF
        images = extract_images_from_pdf(pdf_path)
        
        if not images:
            logging.warning("No images found in PDF, falling back to text-based exam")
            # Fallback to text-based exam if no images found
            pdf_text = extract_text_from_pdf(pdf_path)
            if not pdf_text.strip():
                raise HTTPException(status_code=400, detail="Could not extract content from PDF")
            
            # Generate text-based questions instead
            return await generate_exam_with_ai(pdf_text, "multiple_choice", difficulty, num_questions)
        
        # Configure Google AI
        genai.configure(api_key=GOOGLE_AI_KEY)
        
        # Convert difficulty to Turkish
        difficulty_turkish = {
            "easy": "kolay",
            "medium": "orta", 
            "hard": "zor"
        }.get(difficulty, difficulty)
        
        # Create prompt for image-based questions
        prompt = f"""Sen uzman bir sınav oluşturucususun. Verilen görsellere dayalı olarak yüksek kaliteli sınav soruları oluştur.

Aşağıdaki görsellere dayalı olarak {num_questions} adet {difficulty_turkish} zorluk seviyesinde görsel tabanlı sınav sorusu oluştur.

SORU TÜRÜ TALİMATI:
SADECE görsel tabanlı sorular oluştur!
- Her soru için 5 seçenek (A, B, C, D, E) hazırla
- question_type her zaman 'image_based' olmalı
- options alanını doldur
- correct_answer sadece harf olmalı (A, B, C, D veya E)
- Sorular görseldeki içeriği analiz etmeyi gerektirmeli
- Başka türde soru oluşturma!

GÖRSEL TANIMLAMA TALİMATI:
- Soru metninde "Görsel 0", "Görsel 1" gibi sayfa numaraları KULLANMA!
- Bunun yerine her görselin içeriğini tanımlayan açıklayıcı ifadeler kullan
- Görselin türünü ve içeriğini belirten ifadeler kullan:

ÖRNEKLER:
- "Yukarıdaki akış diyagramına göre..." (süreç diyagramı için)
- "Verilen grafikte gösterilen..." (grafik/chart için)
- "Şemada belirtilen..." (teknik şema için)
- "Tablodaki verilere göre..." (veri tablosu için)
- "Diyagramda gösterilen..." (genel diyagram için)
- "Resimde görülen..." (fotoğraf için)
- "Çizelgede yer alan..." (çizelge için)
- "Haritada işaretlenen..." (harita için)
- "Organizasyon şemasında..." (organizasyon şeması için)
- "Zaman çizelgesinde..." (timeline için)

KURALLAR:
- Görselin ne tür bir içerik olduğunu (diyagram, grafik, tablo, şema, resim vb.) belirt
- Görselin ana konusunu veya amacını kısaca açıkla
- "Yukarıdaki", "Verilen", "Şemada" gibi ifadelerle görsele atıf yap

ÖNEMLİ: 
- TÜM sorular image_based türünde olmalı
- Sadece aşağıdaki yapıda geçerli bir JSON dizisi döndür:
[
  {{
    "question_text": "Yukarıdaki akış diyagramına göre hangi süreç gösterilmektedir?",
    "question_type": "image_based",
    "options": ["A. Seçenek 1", "B. Seçenek 2", "C. Seçenek 3", "D. Seçenek 4", "E. Seçenek 5"],
    "correct_answer": "A",
    "explanation": "Cevabın kısa açıklaması",
    "image_index": 0
  }},
  {{
    "question_text": "Verilen grafikte gösterilen trend hangi dönemi kapsamaktadır?",
    "question_type": "image_based",
    "options": ["A. Seçenek 1", "B. Seçenek 2", "C. Seçenek 3", "D. Seçenek 4", "E. Seçenek 5"],
    "correct_answer": "B",
    "explanation": "Cevabın kısa açıklaması",
    "image_index": 1
  }}
]

JSON dizisinden önce veya sonra herhangi bir metin ekleme.
Her soru için question_type alanını "image_based" olarak ayarla.
image_index 0'dan başlayarak görsel numarasını belirt.
Tüm soruları ve açıklamaları Türkçe dilinde oluştur."""
        
        # Generate content using Gemini with images
        model_names_to_try = ['gemini-2.5-pro', 'gemini-2.5-flash', 'gemini-2.0-flash', 'gemini-pro-latest']
        model = None
        
        for model_name in model_names_to_try:
            try:
                model = genai.GenerativeModel(model_name)
                logging.info(f"Successfully created model for images: {model_name}")
                break
            except Exception as e:
                logging.warning(f"Failed to create model {model_name}: {e}")
                continue
        
        if not model:
            raise HTTPException(status_code=500, detail="No available Gemini models found for image processing")
        
        # Prepare images for Gemini
        image_parts = []
        for i, img_base64 in enumerate(images):
            image_parts.append({
                "mime_type": "image/jpeg",
                "data": img_base64
            })
        
        # Generate content with images
        response = model.generate_content([prompt] + image_parts)
        response_text = response.text.strip()
        
        logging.info(f"AI response for images preview: {response_text[:300]}...")
        
        # Parse response
        import json
        if response_text.startswith("```"):
            response_text = response_text.split("\n", 1)[1]
            response_text = response_text.rsplit("```", 1)[0]
        
        questions_data = json.loads(response_text)
        
        # Convert to Question objects with images
        questions = []
        for q_data in questions_data:
            img_idx = q_data.get("image_index", 0)
            if img_idx < len(images):
                question = Question(
                    question_text=q_data["question_text"],
                    question_type="image_based",
                    options=q_data.get("options"),
                    correct_answer=q_data["correct_answer"],
                    explanation=q_data.get("explanation"),
                    image_data=images[img_idx]  # Attach the base64 image
                )
                questions.append(question)
        
        return questions
    except Exception as e:
        logging.error(f"Error generating image-based exam: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate image-based exam: {str(e)}")

async def generate_exam_with_ai(pdf_text: str, exam_type: str, difficulty: str, num_questions: int) -> List[Question]:
    """Generate exam questions using AI"""
    try:
        # Configure Google AI
        genai.configure(api_key=GOOGLE_AI_KEY)
        
        # Create prompt based on exam type
        type_instruction = {
            "multiple_choice": {
                "instruction": "SADECE çoktan seçmeli sorular oluştur. Her soru için 5 seçenek (A, B, C, D, E) hazırla. Doğru cevap harfini belirt.",
                "question_type": "multiple_choice"
            },
            "true_false": {
                "instruction": "SADECE doğru/yanlış soruları oluştur. Cevap 'Doğru' veya 'Yanlış' olmalı.",
                "question_type": "true_false"
            },
            "fill_blank": {
                "instruction": "SADECE boşluk doldurma soruları oluştur. Boşluğu göstermek için '___' kullan. Doğru cevabı ver.",
                "question_type": "fill_blank"
            },
            "open_ended": {
                "instruction": "SADECE açık uçlu sorular oluştur. Detaylı cevaplar gerektiren sorular hazırla. Örnek doğru cevap ver.",
                "question_type": "open_ended"
            },
            "mixed": {
                "instruction": "Farklı türlerde sorular oluştur: çoktan seçmeli, doğru/yanlış, boşluk doldurma ve açık uçlu soruların karışımını yap.",
                "question_type": "mixed"
            }
        }
        
        # Convert difficulty to Turkish
        difficulty_turkish = {
            "easy": "kolay",
            "medium": "orta", 
            "hard": "zor"
        }.get(difficulty, difficulty)
        
        exam_instruction = type_instruction[exam_type]
        
        if exam_type == "mixed":
            prompt = f"""Sen uzman bir sınav oluşturucususun. Verilen içeriğe dayalı olarak yüksek kaliteli sınav soruları oluştur.

Aşağıdaki içeriğe dayalı olarak {num_questions} adet {difficulty_turkish} zorluk seviyesinde sınav sorusu oluştur.

{exam_instruction["instruction"]}

İçerik:
{pdf_text[:4000]}

ÖNEMLİ: Sadece aşağıdaki yapıda geçerli bir JSON dizisi döndür:
[
  {{
    "question_text": "Soru metni burada",
    "question_type": "multiple_choice" veya "true_false" veya "fill_blank" veya "open_ended",
    "options": ["A. Seçenek 1", "B. Seçenek 2", "C. Seçenek 3", "D. Seçenek 4", "E. Seçenek 5"] (sadece multiple_choice için),
    "correct_answer": "Doğru cevap",
    "explanation": "Cevabın kısa açıklaması"
  }}
]

JSON dizisinden önce veya sonra herhangi bir metin ekleme. Tüm soruları ve açıklamaları Türkçe dilinde oluştur."""
        else:
            prompt = f"""Sen uzman bir sınav oluşturucususun. Verilen içeriğe dayalı olarak yüksek kaliteli sınav soruları oluştur.

Aşağıdaki içeriğe dayalı olarak {num_questions} adet {difficulty_turkish} zorluk seviyesinde sınav sorusu oluştur.

{exam_instruction["instruction"]}

İçerik:
{pdf_text[:4000]}

ÖNEMLİ: 
- TÜM sorular {exam_instruction["question_type"]} türünde olmalı
- Sadece aşağıdaki yapıda geçerli bir JSON dizisi döndür:
[
  {{
    "question_text": "Soru metni burada",
    "question_type": "{exam_instruction["question_type"]}",
    "options": ["A. Seçenek 1", "B. Seçenek 2", "C. Seçenek 3", "D. Seçenek 4", "E. Seçenek 5"] (sadece multiple_choice için),
    "correct_answer": "Doğru cevap",
    "explanation": "Cevabın kısa açıklaması"
  }}
]

JSON dizisinden önce veya sonra herhangi bir metin ekleme.
Her soru için question_type alanını "{exam_instruction["question_type"]}" olarak ayarla.
Tüm soruları ve açıklamaları Türkçe dilinde oluştur."""
        
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
        
        # Log the exam type and prompt for debugging
        logging.info(f"Creating exam with type: {exam_type}")
        logging.info(f"Question type constraint: {exam_instruction['question_type']}")
        logging.info(f"Prompt preview: {prompt[:300]}...")
        
        response = model.generate_content(prompt)
        response_text = response.text.strip()
        
        logging.info(f"AI response preview: {response_text[:300]}...")
        
        # Parse response
        import json
        # Remove markdown code blocks if present
        if response_text.startswith("```"):
            response_text = response_text.split("\n", 1)[1]
            response_text = response_text.rsplit("```", 1)[0]
        
        questions_data = json.loads(response_text)
        
        # Log the question types generated
        question_types = [q.get("question_type") for q in questions_data]
        logging.info(f"Generated question types: {question_types}")
        
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
    exam_type: str = Form("mixed"),
    difficulty: str = Form("medium"),
    num_questions: int = Form(10),
    current_user: dict = Depends(get_current_user)
):
    # Log received parameters for debugging
    logging.info(f"Received exam parameters - Type: {exam_type}, Difficulty: {difficulty}, Questions: {num_questions}")
    
    # Validate PDF
    if not pdf.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    # Save PDF temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        content = await pdf.read()
        tmp_file.write(content)
        tmp_path = tmp_file.name
    
    try:
        # Check if image-based exam
        if exam_type == "image_based":
            # Generate image-based questions directly from PDF
            questions = await generate_image_based_exam(tmp_path, difficulty, num_questions)
        else:
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

@api_router.delete("/exams/{exam_id}")
async def delete_exam(exam_id: str, current_user: dict = Depends(get_current_user)):
    """Delete an exam"""
    # Check if exam exists and belongs to user
    exam = await db.exams.find_one({"id": exam_id, "user_id": current_user["id"]}, {"_id": 0})
    
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    
    # Delete the exam
    result = await db.exams.delete_one({"id": exam_id, "user_id": current_user["id"]})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Exam not found")
    
    # Also delete related exam results
    await db.exam_results.delete_many({"exam_id": exam_id})
    
    return {"message": "Exam deleted successfully"}

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