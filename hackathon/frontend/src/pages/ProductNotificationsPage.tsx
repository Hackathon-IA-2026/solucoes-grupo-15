import { Bell, Check, FileCheck2, FileText, Gavel, Megaphone, Settings, Sparkles, type LucideIcon } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { PageHero } from "../components/layout/PageHero";
import { appRepository } from "../services/appRepository";
import type { AppNotification } from "../types/product";

const categoryIcons: Record<AppNotification["category"], LucideIcon> = { "Processo SEI": FileText, Norma: Gavel, "Consulta Pública": Megaphone, Parecer: FileCheck2, Família: Sparkles };

export function ProductNotificationsPage() {
  const [notifications, setNotifications] = useState<AppNotification[] | null>(null);
  const [filter, setFilter] = useState("Todas");
  useEffect(() => { appRepository.getNotifications().then(setNotifications); }, []);
  const visible = useMemo(() => (notifications ?? []).filter((item) => filter === "Todas" || (filter === "Não lidas" && !item.read) || item.category === filter), [notifications, filter]);

  function markRead(id: string) { setNotifications((items) => items?.map((item) => item.id === id ? { ...item, read: true } : item) ?? null); }
  const unread = notifications?.filter((item) => !item.read).length ?? 0;
  return (
    <div className="product-page"><PageHero icon={Bell} title="Notificações" description="Acompanhe movimentações, documentos e temas relevantes sem acessar diariamente os sistemas da ANEEL." />
      <div className="segmented-control notifications-filters">{["Todas","Não lidas","Processo SEI","Norma","Parecer"].map((item) => <button type="button" className={filter === item ? "active" : ""} key={item} onClick={() => setFilter(item)}>{item}{item === "Não lidas" ? ` (${unread})` : ""}</button>)}</div>
      {!notifications ? <div className="skeleton notifications-skeleton" /> : <div className="notifications-layout"><section className="notification-stream">{visible.length === 0 ? <div className="product-empty"><Bell size={28} /><h3>Nenhuma notificação.</h3><p>Novas movimentações aparecerão aqui.</p></div> : visible.map((notification) => { const Icon = categoryIcons[notification.category]; return <article className={notification.read ? "notification-item read" : "notification-item"} key={notification.id}><span className={`notification-icon notification-${notification.category.toLowerCase().replaceAll(" ", "-")}`}><Icon size={22} /></span><div><h2>{notification.title}</h2><strong>{notification.reference}</strong><p>{notification.description}</p></div><div className="notification-meta"><span className="status-chip blue">{notification.category}</span><time>{notification.createdAt}</time>{!notification.read && <button type="button" onClick={() => markRead(notification.id)}><Check size={15} /> Marcar como lida</button>}</div></article>; })}</section><aside className="summary-sidebar notifications-sidebar"><div className="notification-callout"><Bell size={28} /><h2>Fique sempre atualizada, Carol.</h2><p>Alertas de processo podem incluir data, PDF e resumo do novo documento.</p></div><h3>Seu resumo de hoje</h3><div className="notification-summary"><span><strong>{unread}</strong>Não lidas</span><span><strong>{notifications.filter((item) => item.category === "Processo SEI").length}</strong>Processos</span><span><strong>{notifications.filter((item) => item.category === "Norma").length}</strong>Normas</span></div><h3><Settings size={16} /> Preferências</h3><label className="toggle-row"><span>Movimentações processuais<small>Alerta no sistema e por e-mail</small></span><input type="checkbox" defaultChecked /></label><label className="toggle-row"><span>Novos documentos<small>PDF e resumo do conteúdo</small></span><input type="checkbox" defaultChecked /></label><label className="toggle-row"><span>Atualizações de famílias<small>Novidades nos temas seguidos</small></span><input type="checkbox" defaultChecked /></label></aside></div>}
    </div>
  );
}
