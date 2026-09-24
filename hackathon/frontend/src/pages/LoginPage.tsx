import { Eye, EyeOff, LogIn, LockKeyhole, Mail, ShieldCheck } from "lucide-react";
import { useState, type FormEvent } from "react";
import { Navigate, useNavigate } from "react-router-dom";

import { useSession } from "../features/auth/SessionContext";

export function LoginPage() {
  const navigate = useNavigate();
  const { user, login } = useSession();
  const [email, setEmail] = useState("carolina@capiwatt.demo");
  const [password, setPassword] = useState("demo-capiwatt");
  const [showPassword, setShowPassword] = useState(false);
  const [remember, setRemember] = useState(true);
  const [error, setError] = useState("");

  if (user) return <Navigate to="/escolher-perfil" replace />;

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!email.trim() || password.length < 4) {
      setError("Informe um e-mail e uma senha com pelo menos 4 caracteres.");
      return;
    }
    login(email.trim());
    navigate("/escolher-perfil");
  }

  return (
    <main className="login-page">
      <section className="login-brand-panel" aria-label="CapiWatt Lens, feito no Brasil, ligado no futuro"><img src="/assets/login-brand-panel.png" alt="CapiWatt Lens, energia, tecnologia e regulação no Brasil" /></section>
      <section className="login-form-panel">
        <form className="login-card" onSubmit={submit}>
          <div className="login-heading"><span className="mobile-logo">Capi<span>Watt</span> Lens</span><h1>Entrar</h1><p>Acesse sua conta para continuar.</p></div>
          <label htmlFor="email">E-mail ou usuário</label>
          <div className="field-control"><Mail size={20} /><input id="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="seu@email.com ou usuário" autoComplete="username" /></div>
          <label htmlFor="password">Senha</label>
          <div className="field-control"><LockKeyhole size={20} /><input id="password" type={showPassword ? "text" : "password"} value={password} onChange={(event) => setPassword(event.target.value)} placeholder="Sua senha" autoComplete="current-password" /><button type="button" onClick={() => setShowPassword((visible) => !visible)} aria-label={showPassword ? "Ocultar senha" : "Mostrar senha"}>{showPassword ? <EyeOff size={20} /> : <Eye size={20} />}</button></div>
          <label className="remember-control"><input type="checkbox" checked={remember} onChange={(event) => setRemember(event.target.checked)} /> <span>Manter conectado</span></label>
          {error && <p className="form-error" role="alert">{error}</p>}
          <button className="yellow-button login-submit" type="submit"><LogIn size={21} /> Entrar</button>
          <button type="button" className="text-button">Esqueci minha senha</button>
          <div className="provision-note"><ShieldCheck size={19} /><p>Sem cadastro self-service.<br />O acesso é provisionado pela equipe.</p></div>
        </form>
      </section>
    </main>
  );
}
