import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import { toast } from "sonner";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { FileText, Plus, LogOut, History, TrendingUp, BookOpen, Trash2 } from "lucide-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function Dashboard() {
  const navigate = useNavigate();
  const [exams, setExams] = useState([]);
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState(null);

  useEffect(() => {
    const userData = localStorage.getItem("user");
    if (userData) {
      setUser(JSON.parse(userData));
    }
    fetchExams();
  }, []);

  const fetchExams = async () => {
    try {
      const response = await axios.get(`${API}/exams`);
      setExams(response.data);
    } catch (error) {
      toast.error("Sınavlar yüklenemedi");
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    toast.success("Çıkış yapıldı");
    window.location.href = "/auth";
  };

  const getDifficultyColor = (difficulty) => {
    switch (difficulty) {
      case "easy": return "#10b981";
      case "medium": return "#f59e0b";
      case "hard": return "#ef4444";
      default: return "#6b7280";
    }
  };

  const getExamTypeLabel = (type) => {
    const labels = {
      multiple_choice: "Çoktan Seçmeli",
      true_false: "Doğru/Yanlış",
      fill_blank: "Boşluk Doldurma",
      open_ended: "Klasik",
      mixed: "Karışık"
    };
    return labels[type] || type;
  };

  const handleDeleteExam = async (examId, examTitle, event) => {
    event.stopPropagation(); // Prevent card click
    
    if (window.confirm(`"${examTitle}" sınavını silmek istediğinizden emin misiniz? Bu işlem geri alınamaz.`)) {
      try {
        await axios.delete(`${API}/exams/${examId}`);
        toast.success("Sınav başarıyla silindi");
        fetchExams(); // Refresh the list
      } catch (error) {
        toast.error("Sınav silinirken hata oluştu");
        console.error("Delete error:", error);
      }
    }
  };

  return (
    <div className="min-h-screen" style={{ background: 'linear-gradient(135deg, #e0e7ff 0%, #f3e8ff 100%)' }}>
      {/* Header */}
      <header className="glass-card border-b">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}>
              <FileText className="w-6 h-6 text-white" />
            </div>
            <h1 className="text-2xl font-bold" style={{ color: '#667eea' }}>ExamGenerator</h1>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-gray-700 font-medium" data-testid="user-name">Hoş geldin, {user?.full_name}</span>
            <Button variant="outline" onClick={handleLogout} data-testid="logout-button">
              <LogOut className="w-4 h-4 mr-2" />
              Çıkış
            </Button>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* Stats Cards */}
        <div className="grid md:grid-cols-3 gap-6 mb-8 fade-in">
          <Card className="glass-card border-none hover-lift">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-600 text-sm font-medium">Toplam Sınav</p>
                  <p className="text-3xl font-bold mt-2" style={{ color: '#667eea' }} data-testid="total-exams">{exams.length}</p>
                </div>
                <div className="w-14 h-14 rounded-2xl flex items-center justify-center" style={{ background: 'rgba(102, 126, 234, 0.1)' }}>
                  <BookOpen className="w-7 h-7" style={{ color: '#667eea' }} />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="glass-card border-none hover-lift cursor-pointer" onClick={() => navigate('/results')} data-testid="results-card">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-600 text-sm font-medium">Sınav Geçmişi</p>
                  <p className="text-3xl font-bold mt-2" style={{ color: '#667eea' }}>Görüntüle</p>
                </div>
                <div className="w-14 h-14 rounded-2xl flex items-center justify-center" style={{ background: 'rgba(102, 126, 234, 0.1)' }}>
                  <History className="w-7 h-7" style={{ color: '#667eea' }} />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="glass-card border-none hover-lift">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-600 text-sm font-medium">Ortalama Başarı</p>
                  <p className="text-3xl font-bold mt-2" style={{ color: '#10b981' }}>-</p>
                </div>
                <div className="w-14 h-14 rounded-2xl flex items-center justify-center" style={{ background: 'rgba(16, 185, 129, 0.1)' }}>
                  <TrendingUp className="w-7 h-7" style={{ color: '#10b981' }} />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Create New Exam Button */}
        <div className="mb-8 fade-in">
          <Button
            className="btn-primary text-lg py-6 px-8"
            onClick={() => navigate('/create')}
            data-testid="create-exam-button"
          >
            <Plus className="w-5 h-5 mr-2" />
            Yeni Sınav Oluştur
          </Button>
        </div>

        {/* Exams List */}
        <div>
          <h2 className="text-2xl font-bold mb-6" style={{ color: '#1f2937' }}>Sınavlarınız</h2>
          
          {loading ? (
            <div className="flex justify-center py-12">
              <div className="spinner"></div>
            </div>
          ) : exams.length === 0 ? (
            <Card className="glass-card border-none">
              <CardContent className="py-12 text-center">
                <FileText className="w-16 h-16 mx-auto mb-4 opacity-30" />
                <p className="text-gray-600">Henüz sınav oluşturmadınız</p>
                <Button className="btn-primary mt-4" onClick={() => navigate('/create')}>
                  İlk Sınavını Oluştur
                </Button>
              </CardContent>
            </Card>
          ) : (
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6" data-testid="exams-list">
              {exams.map((exam) => (
                <Card
                  key={exam.id}
                  className="glass-card border-none hover-lift cursor-pointer"
                  onClick={() => navigate(`/exam/${exam.id}`)}
                  data-testid={`exam-card-${exam.id}`}
                >
                  <CardHeader>
                    <div className="flex items-start justify-between mb-2">
                      <div className="w-12 h-12 rounded-xl flex items-center justify-center" style={{ background: 'rgba(102, 126, 234, 0.1)' }}>
                        <FileText className="w-6 h-6" style={{ color: '#667eea' }} />
                      </div>
                      <div className="flex items-center gap-2">
                        <span
                          className="px-3 py-1 rounded-full text-xs font-semibold text-white"
                          style={{ background: getDifficultyColor(exam.difficulty) }}
                        >
                          {exam.difficulty === 'easy' ? 'Kolay' : exam.difficulty === 'medium' ? 'Orta' : 'Zor'}
                        </span>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-8 w-8 p-0 text-red-500 hover:text-red-700 hover:bg-red-50"
                          onClick={(e) => handleDeleteExam(exam.id, exam.title, e)}
                          data-testid={`delete-exam-${exam.id}`}
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
                    </div>
                    <CardTitle className="text-lg line-clamp-2">{exam.title}</CardTitle>
                    <CardDescription>
                      {getExamTypeLabel(exam.exam_type)} • {exam.questions?.length || 0} Soru
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-gray-600">
                      {new Date(exam.created_at).toLocaleDateString('tr-TR', {
                        day: 'numeric',
                        month: 'long',
                        year: 'numeric'
                      })}
                    </p>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
