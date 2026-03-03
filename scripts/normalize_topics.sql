-- Нормализуем topic к нижнему регистру и переводим английские на русский
UPDATE telegram_chats SET topic = 
  CASE LOWER(topic)
    WHEN 'business' THEN 'бизнес'
    WHEN 'marketing' THEN 'маркетинг'
    WHEN 'it' THEN 'it'
    WHEN 'finance' THEN 'финансы'
    WHEN 'crypto' THEN 'крипто'
    WHEN 'education' THEN 'образование'
    WHEN 'news' THEN 'новости'
    WHEN 'health' THEN 'здоровье'
    WHEN 'courses' THEN 'образование'
    WHEN 'other' THEN 'other'
    ELSE LOWER(topic)
  END
WHERE is_active = true;

-- Проверяем результат
SELECT topic, COUNT(*) as count FROM telegram_chats WHERE is_active = true GROUP BY topic ORDER BY count DESC;
