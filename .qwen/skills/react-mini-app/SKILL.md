---
name: react-mini-app
description: "MUST BE USED for Telegram Mini App frontend: React 19 + TypeScript + Vite, glassmorphism design, Tailwind CSS, @twa-dev/sdk, Zustand store, recharts charts, react-router-dom navigation. Use when editing mini_app/src/, creating UI components, pages, or Telegram WebApp integrations. Enforces: dark/light theme via Telegram.WebApp.colorScheme, no inline styles except glassmorphism, custom hooks for API data."
license: MIT
version: 1.0.0
author: market-telegram-bot
---

# React Mini App Conventions

Создаёт компоненты Telegram Mini App на React 19 + TypeScript.
Дизайн — glassmorphism, темы — из Telegram.WebApp, данные — через axios с JWT.

## When to Use
- Создание новых страниц в `mini_app/src/pages/`
- Написание переиспользуемых компонентов в `mini_app/src/components/`
- Интеграция с Telegram WebApp SDK (`@twa-dev/sdk`)
- Добавление графиков аналитики через recharts
- Настройка zustand-стора
- Написание хуков для API-запросов

## Rules
- Все API-вызовы — через `src/api/client.ts` (axios с JWT interceptor)
- Читать тему: `const { colorScheme } = useTelegramWebApp()` — применять CSS-переменные
- Glassmorphism card: `backdrop-filter: blur(12px); background: rgba(255,255,255,0.1)`
- Никаких inline-стилей кроме glassmorphism — использовать Tailwind utility classes
- Все запросы данных — через кастомные хуки (`useCampaigns`, `useAnalytics`, etc.)
- Показывать loading-скелетон пока данные загружаются, error boundary при ошибках

## Instructions

1. Создай компонент в `mini_app/src/components/<Feature>/` или страницу в `pages/`
2. Используй `useTelegramWebApp()` для получения темы и данных пользователя
3. Оберни карточки в `<GlassCard>` компонент
4. Данные загружай через кастомный хук с `useEffect` + `useState`
5. Для графиков — `recharts` с цветами из Telegram-темы
6. Экспортируй через `export default`

## Examples

### GlassCard Component
```tsx
// mini_app/src/components/ui/GlassCard.tsx
interface GlassCardProps {
  children: React.ReactNode;
  className?: string;
}

export const GlassCard: React.FC<GlassCardProps> = ({ children, className = "" }) => (
  <div
    className={`rounded-2xl p-4 border border-white/20 ${className}`}
    style={{
      background: "rgba(255,255,255,0.1)",
      backdropFilter: "blur(12px)",
      WebkitBackdropFilter: "blur(12px)",
    }}
  >
    {children}
  </div>
);
```

### useTelegramWebApp Hook
```tsx
// mini_app/src/hooks/useTelegramWebApp.ts
import { useEffect } from "react";

export function useTelegramWebApp() {
  const tg = window.Telegram?.WebApp;

  useEffect(() => {
    tg?.ready();
    tg?.expand();
  }, []);

  return {
    tg,
    user: tg?.initDataUnsafe?.user,
    colorScheme: tg?.colorScheme ?? "light",
    initData: tg?.initData ?? "",
  };
}
```

### Data Fetching Hook
```tsx
// mini_app/src/hooks/useCampaigns.ts
import { useState, useEffect } from "react";
import { apiClient } from "../api/client";
import type { Campaign } from "../types";

export function useCampaigns() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiClient.get<Campaign[]>("/campaigns")
      .then(res => setCampaigns(res.data))
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  return { campaigns, loading, error };
}
```

### Analytics Chart
```tsx
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";

interface AnalyticsChartProps {
  data: { date: string; sent: number; clicked: number }[];
}

export const AnalyticsChart: React.FC<AnalyticsChartProps> = ({ data }) => (
  <ResponsiveContainer width="100%" height={200}>
    <LineChart data={data}>
      <XAxis dataKey="date" stroke="#94a3b8" fontSize={12} />
      <YAxis stroke="#94a3b8" fontSize={12} />
      <Tooltip contentStyle={{ background: "rgba(15,23,42,0.8)", border: "none", borderRadius: 8 }} />
      <Line type="monotone" dataKey="sent" stroke="#6366f1" strokeWidth={2} dot={false} />
      <Line type="monotone" dataKey="clicked" stroke="#22d3ee" strokeWidth={2} dot={false} />
    </LineChart>
  </ResponsiveContainer>
);
```

### Zustand Store
```tsx
// mini_app/src/store/campaignStore.ts
import { create } from "zustand";
import type { Campaign } from "../types";

interface CampaignStore {
  selected: Campaign | null;
  setSelected: (c: Campaign | null) => void;
}

export const useCampaignStore = create<CampaignStore>((set) => ({
  selected: null,
  setSelected: (c) => set({ selected: c }),
}));
```
