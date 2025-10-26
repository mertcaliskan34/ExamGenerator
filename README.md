# Exam Generator

AI-powered exam generation system that creates intelligent questions from PDF documents using Google's Gemini AI technology.

## Overview

Exam Generator is a full-stack web application that allows users to upload PDF documents and automatically generate comprehensive exam questions. The system uses advanced AI to analyze document content and create various question types with appropriate difficulty levels.

## Features

- **PDF Document Processing**: Upload and extract text from PDF files
- **AI-Powered Question Generation**: Uses Google Gemini 2.5 Pro for intelligent question creation
- **Multiple Question Types**: 
  - Multiple Choice Questions
  - True/False Questions
  - Fill in the Blank Questions
  - Open-ended Questions
- **Configurable Difficulty**: Easy, Medium, and Hard difficulty levels
- **User Authentication**: Secure user registration and login system
- **Interactive Exam Interface**: User-friendly exam taking experience
- **Detailed Results**: Comprehensive exam results with feedback and explanations
- **Responsive Design**: Modern, mobile-friendly interface

## Technology Stack

### Backend
- **FastAPI**: Modern, fast web framework for building APIs
- **MongoDB**: NoSQL database for storing user data and exam content
- **Google Gemini AI**: Advanced AI for question generation
- **PyPDF2**: PDF text extraction library
- **JWT**: Secure authentication tokens
- **Python 3.10+**: Programming language

### Frontend
- **React 19**: Modern frontend framework
- **Tailwind CSS**: Utility-first CSS framework
- **Radix UI**: Accessible component library
- **React Router**: Client-side routing
- **Axios**: HTTP client for API communication

## Prerequisites

Before running this application, ensure you have the following installed:

- Node.js 18 or higher
- Python 3.10 or higher
- MongoDB (local installation or cloud service)
- Google AI API key

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/mertcaliskan34/exam-generator.git
cd exam-generator
```

### 2. Backend Setup

Navigate to the backend directory and set up the Python environment:

```bash
cd backend
python -m venv venv

# Activate virtual environment
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Frontend Setup

Navigate to the frontend directory and install dependencies:

```bash
cd frontend
npm install
# or
yarn install
```

### 4. Environment Configuration

Create environment files for both backend and frontend:

**Backend (.env file in backend directory):**
```env
MONGO_URL=mongodb://localhost:27017
DB_NAME=exam_generator
CORS_ORIGINS=*
GOOGLE_AI_KEY=your_google_ai_api_key_here
```

**Frontend (.env file in frontend directory):**
```env
REACT_APP_BACKEND_URL=http://localhost:8000
WDS_SOCKET_PORT=3000
REACT_APP_ENABLE_VISUAL_EDITS=true
ENABLE_HEALTH_CHECK=false
```

### 5. Database Setup

Start MongoDB using Docker:

```bash
docker run -d -p 27017:27017 --name mongodb mongo:latest
```

Or install MongoDB locally and start the service.

## Running the Application

### Start the Backend Server

```bash
cd backend
uvicorn server:app --reload --host 0.0.0.0 --port 8000
```

The backend API will be available at `http://localhost:8000`

### Start the Frontend Development Server

```bash
cd frontend
npm start
# or
yarn start
```

The frontend application will be available at `http://localhost:3000`

### Access Points

- **Frontend Application**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## Usage

1. **User Registration**: Create a new account or login with existing credentials
2. **Upload PDF**: Upload a PDF document containing the content for exam generation
3. **Configure Exam Settings**: 
   - Select question type (multiple choice, true/false, fill in blank, open-ended, or mixed)
   - Choose difficulty level (easy, medium, hard)
   - Specify number of questions (5-50)
4. **Generate Exam**: The AI will analyze the PDF and create exam questions
5. **Take Exam**: Answer the generated questions through the interactive interface
6. **View Results**: Review detailed results with correct answers and explanations

## API Endpoints

### Authentication
- `POST /api/auth/register` - User registration
- `POST /api/auth/login` - User login

### Exam Management
- `POST /api/exams/create` - Create exam from PDF upload
- `GET /api/exams` - Retrieve user's exams
- `GET /api/exams/{exam_id}` - Get specific exam details

### Exam Taking
- `POST /api/exams/submit` - Submit exam answers
- `GET /api/results` - Get user's exam results
- `GET /api/results/{result_id}` - Get specific result details

## Project Structure

```
exam-generator/
├── backend/
│   ├── server.py             # Main FastAPI application
│   ├── requirements.txt      # Python dependencies
│   └── .env                  # Environment variables
├── frontend/
│   ├── src/
│   │   ├── components/       # Reusable UI components
│   │   ├── pages/            # Application pages
│   │   ├── hooks/            # Custom React hooks
│   │   └── lib/              # Utility functions
│   ├── public/               # Static assets
│   ├── package.json          # Node.js dependencies
│   └── .env                  # Frontend environment variables
├── .gitignore                # Git ignore rules
├── LICENSE                   # MIT License
└── README.md                 # This file
```

## Configuration

### Backend Configuration

The backend can be configured through environment variables:

- `MONGO_URL`: MongoDB connection string
- `DB_NAME`: Database name
- `CORS_ORIGINS`: Allowed CORS origins
- `GOOGLE_AI_KEY`: Google AI API key
- `SECRET_KEY`: JWT secret key (optional)

### Frontend Configuration

The frontend can be configured through environment variables:

- `REACT_APP_BACKEND_URL`: Backend API URL
- `WDS_SOCKET_PORT`: Webpack dev server port
- `REACT_APP_ENABLE_VISUAL_EDITS`: Enable visual editing features
- `ENABLE_HEALTH_CHECK`: Enable health check features

## Development

### Backend Development

The backend uses FastAPI with automatic API documentation. After starting the server, visit `http://localhost:8000/docs` for interactive API documentation.

### Frontend Development

The frontend uses React with hot reloading. Changes to the source code will automatically refresh the browser.

### Code Quality

- Backend: Python with type hints and FastAPI best practices
- Frontend: React with modern hooks and functional components
- Styling: Tailwind CSS for consistent design
- Components: Radix UI for accessible components

## Deployment

### Backend Deployment

1. Install production dependencies
2. Set up environment variables
3. Configure MongoDB connection
4. Deploy using uvicorn or similar ASGI server

### Frontend Deployment

1. Build the production bundle: `npm run build`
2. Serve the built files using a web server
3. Configure environment variables for production

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/new-feature`
3. Commit your changes: `git commit -m 'Add new feature'`
4. Push to the branch: `git push origin feature/new-feature`
5. Open a Pull Request

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Support

For support and questions, please open an issue on the GitHub repository.

## Acknowledgments

- Google Gemini AI for advanced question generation capabilities
- Radix UI for accessible and beautiful components
- Tailwind CSS for efficient styling
- FastAPI for the robust and fast backend framework
