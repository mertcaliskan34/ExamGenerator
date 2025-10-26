import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import { toast } from "sonner";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { ArrowLeft, Trophy, Clock, CheckCircle, XCircle } from "lucide-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function ResultsPage() {
  const navigate = useNavigate();
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchResults();
  }, []);

  const fetchResults = async () => {
    try {
      const response = await axios.get(`${API}/results`);
      setResults(response.data);
    } catch (error) {
      toast.error("Sonuçlar yüklenemedi");
    } finally {
      setLoading(false);
    }
  };

  const getScoreColor = (score) => {
    if (score >= 80) return '#10b981';
    if (score >= 60) return '#f59e0b';
    return '#ef4444';
  };

  return (
    <div className="min-h-screen" style={{ background: 'linear-gradient(135deg, #e0e7ff 0%, #f3e8ff 100%)' }}>
      {/* Header */}
      <header className="glass-card border-b">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center gap-4">
          <Button variant="outline" onClick={() => navigate('/')} data-testid="back-to-dashboard">
            <ArrowLeft className="w-4 h-4" />
          </Button>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}>
              <Trophy className="w-6 h-6 text-white" />
            </div>
            <h1 className="text-2xl font-bold" style={{ color: '#667eea' }}>Sınav Geçmişi</h1>
          </div>
        </div>
      </header>

      <div className="max-w-5xl mx-auto px-6 py-8">
        {loading ? (
          <div className="flex justify-center py-12">
            <div className="spinner"></div>
          </div>
        ) : results.length === 0 ? (
          <Card className="glass-card border-none">
            <CardContent className="py-12 text-center">
              <Trophy className="w-16 h-16 mx-auto mb-4 opacity-30" />
              <p className="text-gray-600">Henüz hiç sınav çözmediniz</p>
              <Button className="btn-primary mt-4" onClick={() => navigate('/')}>
                Sınavlara Dön
              </Button>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-6" data-testid="results-list">
            {results.map((result) => (
              <Card
                key={result.id}
                className="glass-card border-none hover-lift cursor-pointer"
                onClick={() => navigate(`/results/${result.id}`)}
                data-testid={`result-card-${result.id}`}
              >
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-6 flex-1">
                      {/* Score Circle */}
                      <div
                        className="w-20 h-20 rounded-full flex items-center justify-center text-2xl font-bold text-white flex-shrink-0"
                        style={{ background: getScoreColor(result.score) }}
                      >
                        {Math.round(result.score)}%
                      </div>

                      {/* Details */}
                      <div className="flex-1">
                        <h3 className="text-lg font-semibold text-gray-800 mb-2" data-testid={`result-exam-id-${result.id}`}>Sınav ID: {result.exam_id}</h3>
                        <div className="flex items-center gap-6 text-sm text-gray-600">
                          <div className="flex items-center gap-2">
                            <CheckCircle className="w-4 h-4" style={{ color: '#10b981' }} />
                            <span><strong>{result.correct_answers}</strong> doğru</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <XCircle className="w-4 h-4" style={{ color: '#ef4444' }} />
                            <span><strong>{result.total_questions - result.correct_answers}</strong> yanlış</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <Clock className="w-4 h-4 text-gray-500" />
                            <span>{new Date(result.submitted_at).toLocaleDateString('tr-TR')}</span>
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* View Details Button */}
                    <Button variant="outline" className="ml-4">
                      Detayları Gör
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
