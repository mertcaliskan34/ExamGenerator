import { useState } from "react";
import axios from "axios";
import { toast } from "sonner";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import { FileText, Brain, Target, Zap } from "lucide-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function AuthPage({ setIsAuthenticated }) {
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    email: "",
    password: "",
    full_name: ""
  });

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const response = await axios.post(`${API}/auth/login`, {
        email: formData.email,
        password: formData.password
      });

      localStorage.setItem("token", response.data.token);
      localStorage.setItem("user", JSON.stringify(response.data.user));
      toast.success("Giriş başarılı!");
      setIsAuthenticated(true);
    } catch (error) {
      toast.error(error.response?.data?.detail || "Giriş başarısız");
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const response = await axios.post(`${API}/auth/register`, formData);

      localStorage.setItem("token", response.data.token);
      localStorage.setItem("user", JSON.stringify(response.data.user));
      toast.success("Kayıt başarılı!");
      setIsAuthenticated(true);
    } catch (error) {
      toast.error(error.response?.data?.detail || "Kayıt başarısız");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4" style={{ background: 'linear-gradient(135deg, #e0e7ff 0%, #f3e8ff 100%)' }}>
      <div className="w-full max-w-6xl grid md:grid-cols-2 gap-8 items-center">
        {/* Left Side - Branding */}
        <div className="text-center md:text-left space-y-6 fade-in">
          <div className="flex items-center justify-center md:justify-start gap-3">
            <div className="w-14 h-14 rounded-2xl flex items-center justify-center" style={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}>
              <FileText className="w-8 h-8 text-white" />
            </div>
            <h1 className="text-5xl font-bold" style={{ color: '#667eea' }}>ExamGenerator</h1>
          </div>
          
          <p className="text-lg text-gray-700 leading-relaxed">
            PDF'lerinizi yapay zeka ile analiz ederek her zorluk seviyesinde profesyonel sınavlar oluşturun.
          </p>

          <div className="space-y-4 mt-8">
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 rounded-xl flex items-center justify-center" style={{ background: 'rgba(102, 126, 234, 0.1)' }}>
                <Brain className="w-6 h-6" style={{ color: '#667eea' }} />
              </div>
              <div>
                <h3 className="font-semibold text-lg text-gray-800">AI Destekli</h3>
                <p className="text-gray-600">Yapay zeka ile akıllı soru üretimi</p>
              </div>
            </div>

            <div className="flex items-start gap-4">
              <div className="w-12 h-12 rounded-xl flex items-center justify-center" style={{ background: 'rgba(102, 126, 234, 0.1)' }}>
                <Target className="w-6 h-6" style={{ color: '#667eea' }} />
              </div>
              <div>
                <h3 className="font-semibold text-lg text-gray-800">Çoklu Format</h3>
                <p className="text-gray-600">Test, klasik, boşluk doldurma ve daha fazlası</p>
              </div>
            </div>

            <div className="flex items-start gap-4">
              <div className="w-12 h-12 rounded-xl flex items-center justify-center" style={{ background: 'rgba(102, 126, 234, 0.1)' }}>
                <Zap className="w-6 h-6" style={{ color: '#667eea' }} />
              </div>
              <div>
                <h3 className="font-semibold text-lg text-gray-800">Hızlı Değerlendirme</h3>
                <p className="text-gray-600">Anında sonuç ve detaylı geri bildirim</p>
              </div>
            </div>
          </div>
        </div>

        {/* Right Side - Auth Form */}
        <Card className="glass-card border-none shadow-2xl">
          <CardHeader>
            <CardTitle className="text-2xl">Hoş Geldiniz</CardTitle>
            <CardDescription>Hesabınıza giriş yapın veya yeni hesap oluşturun</CardDescription>
          </CardHeader>
          <CardContent>
            <Tabs defaultValue="login" className="w-full">
              <TabsList className="grid w-full grid-cols-2 mb-6">
                <TabsTrigger value="login" data-testid="login-tab">Giriş Yap</TabsTrigger>
                <TabsTrigger value="register" data-testid="register-tab">Kayıt Ol</TabsTrigger>
              </TabsList>

              <TabsContent value="login">
                <form onSubmit={handleLogin} className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="login-email">E-posta</Label>
                    <Input
                      id="login-email"
                      data-testid="login-email-input"
                      type="email"
                      placeholder="ornek@email.com"
                      value={formData.email}
                      onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                      required
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="login-password">Şifre</Label>
                    <Input
                      id="login-password"
                      data-testid="login-password-input"
                      type="password"
                      value={formData.password}
                      onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                      required
                    />
                  </div>
                  <Button
                    type="submit"
                    data-testid="login-submit-button"
                    className="w-full btn-primary"
                    disabled={loading}
                  >
                    {loading ? "Giriş yapılıyor..." : "Giriş Yap"}
                  </Button>
                </form>
              </TabsContent>

              <TabsContent value="register">
                <form onSubmit={handleRegister} className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="register-name">Ad Soyad</Label>
                    <Input
                      id="register-name"
                      data-testid="register-name-input"
                      type="text"
                      placeholder="Adınız Soyadınız"
                      value={formData.full_name}
                      onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                      required
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="register-email">E-posta</Label>
                    <Input
                      id="register-email"
                      data-testid="register-email-input"
                      type="email"
                      placeholder="ornek@email.com"
                      value={formData.email}
                      onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                      required
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="register-password">Şifre</Label>
                    <Input
                      id="register-password"
                      data-testid="register-password-input"
                      type="password"
                      value={formData.password}
                      onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                      required
                    />
                  </div>
                  <Button
                    type="submit"
                    data-testid="register-submit-button"
                    className="w-full btn-primary"
                    disabled={loading}
                  >
                    {loading ? "Kayıt yapılıyor..." : "Kayıt Ol"}
                  </Button>
                </form>
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
