import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import axios from "axios";
import { toast } from "sonner";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { ArrowLeft, CheckCircle, XCircle, Trophy } from "lucide-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function ResultDetail() {
  const { resultId } = useParams();
  const navigate = useNavigate();
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchResult();
  }, [resultId]);

  const fetchResult = async () => {
    try {
      const response = await axios.get(`${API}/results/${resultId}`);
      setResult(response.data);
    } catch (error) {
      toast.error("Sonuç yüklenemedi");
      navigate('/results');
    } finally {
      setLoading(false);
    }
  };

  const getScoreColor = (score) => {
    if (score >= 80) return '#10b981';
    if (score >= 60) return '#f59e0b';
    return '#ef4444';
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="spinner"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen" style={{ background: 'linear-gradient(135deg, #e0e7ff 0%, #f3e8ff 100%)' }}>
      {/* Header */}
      <header className="glass-card border-b">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center gap-4">
          <Button variant="outline" onClick={() => navigate('/results')} data-testid="back-to-results">
            <ArrowLeft className="w-4 h-4" />
          </Button>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}>
              <Trophy className="w-6 h-6 text-white" />
            </div>
            <h1 className="text-2xl font-bold" style={{ color: '#667eea' }}>Sınav Sonucu</h1>
          </div>
        </div>
      </header>

      <div className="max-w-4xl mx-auto px-6 py-8">
        {/* Score Summary */}
        <Card className="glass-card border-none shadow-2xl mb-8 fade-in">
          <CardContent className="pt-8">
            <div className="flex flex-col md:flex-row items-center justify-around gap-8">
              {/* Score Circle */}
              <div className="text-center">
                <div
                  className="w-32 h-32 rounded-full flex items-center justify-center text-4xl font-bold text-white mx-auto mb-3"
                  style={{ background: getScoreColor(result.score) }}
                  data-testid="score-display"
                >
                  {Math.round(result.score)}%
                </div>
                <p className="text-gray-600 font-medium">Genel Puanınız</p>
              </div>

              {/* Stats */}
              <div className="grid grid-cols-2 gap-8">
                <div className="text-center">
                  <div className="w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-2" style={{ background: 'rgba(16, 185, 129, 0.1)' }}>
                    <CheckCircle className="w-8 h-8" style={{ color: '#10b981' }} />
                  </div>
                  <p className="text-3xl font-bold" style={{ color: '#10b981' }} data-testid="correct-count">{result.correct_answers}</p>
                  <p className="text-sm text-gray-600">Doğru</p>
                </div>

                <div className="text-center">
                  <div className="w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-2" style={{ background: 'rgba(239, 68, 68, 0.1)' }}>
                    <XCircle className="w-8 h-8" style={{ color: '#ef4444' }} />
                  </div>
                  <p className="text-3xl font-bold" style={{ color: '#ef4444' }} data-testid="incorrect-count">{result.total_questions - result.correct_answers}</p>
                  <p className="text-sm text-gray-600">Yanlış</p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Detailed Feedback */}
        <h2 className="text-2xl font-bold mb-6" style={{ color: '#1f2937' }}>Detaylı Değerlendirme</h2>
        <div className="space-y-6" data-testid="feedback-list">
          {result.feedback.map((item, index) => (
            <Card
              key={item.question_id}
              className={`glass-card border-2 ${item.is_correct ? 'border-green-200' : 'border-red-200'}`}
              data-testid={`feedback-card-${item.question_id}`}
            >
              <CardHeader>
                <div className="flex items-start gap-4">
                  <div
                    className="w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0"
                    style={{ background: item.is_correct ? '#10b981' : '#ef4444' }}
                  >
                    {item.is_correct ? (
                      <CheckCircle className="w-6 h-6 text-white" />
                    ) : (
                      <XCircle className="w-6 h-6 text-white" />
                    )}
                  </div>
                  <div className="flex-1">
                    <CardTitle className="text-lg">Soru {index + 1}</CardTitle>
                    <CardDescription className="mt-2">
                      <span className={`px-3 py-1 rounded-full text-xs font-semibold ${
                        item.is_correct ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                      }`}>
                        {item.is_correct ? 'Doğru' : 'Yanlış'}
                      </span>
                    </CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <p className="text-sm font-semibold text-gray-700 mb-1">Sizin Cevabınız:</p>
                  <p className="text-base" data-testid={`user-answer-${item.question_id}`}>{item.user_answer || "Cevaplanmadı"}</p>
                </div>
                {!item.is_correct && (
                  <div>
                    <p className="text-sm font-semibold text-gray-700 mb-1">Doğru Cevap:</p>
                    <p className="text-base text-green-700 font-medium" data-testid={`correct-answer-${item.question_id}`}>{item.correct_answer}</p>
                  </div>
                )}
                {item.explanation && (
                  <div className="bg-gray-50 rounded-lg p-4">
                    <p className="text-sm font-semibold text-gray-700 mb-1">Açıklama:</p>
                    <p className="text-sm text-gray-600" data-testid={`explanation-${item.question_id}`}>{item.explanation}</p>
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Actions */}
        <div className="mt-8 flex justify-center gap-4">
          <Button variant="outline" onClick={() => navigate('/results')} data-testid="view-all-results">
            Tüm Sonuçlar
          </Button>
          <Button className="btn-primary" onClick={() => navigate('/')} data-testid="back-to-home">
            Ana Sayfaya Dön
          </Button>
        </div>
      </div>
    </div>
  );
}
