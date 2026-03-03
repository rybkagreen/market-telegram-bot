-- Обновляем описания для каналов с разными категориями
-- IT категория
UPDATE telegram_chats SET description = 'python javascript golang rust программирование разработка' 
WHERE LOWER(topic) = 'it' AND (description IS NULL OR description = '') 
AND id IN (SELECT id FROM telegram_chats WHERE LOWER(topic) = 'it' AND (description IS NULL OR description = '') LIMIT 20);

-- Образование
UPDATE telegram_chats SET description = 'онлайн курсы обучение университет школа образование' 
WHERE LOWER(topic) = 'образование' AND (description IS NULL OR description = '')
AND id IN (SELECT id FROM telegram_chats WHERE LOWER(topic) = 'образование' AND (description IS NULL OR description = '') LIMIT 20);

-- Товары
UPDATE telegram_chats SET description = 'товары магазин покупки распродажи кэшбэк промокоды' 
WHERE LOWER(topic) = 'товары' AND (description IS NULL OR description = '')
AND id IN (SELECT id FROM telegram_chats WHERE LOWER(topic) = 'товары' AND (description IS NULL OR description = '') LIMIT 20);

-- Услуги
UPDATE telegram_chats SET description = 'услуги сервис помощь заказ выполнение работа' 
WHERE LOWER(topic) = 'услуги' AND (description IS NULL OR description = '')
AND id IN (SELECT id FROM telegram_chats WHERE LOWER(topic) = 'услуги' AND (description IS NULL OR description = '') LIMIT 20);

-- Здоровье
UPDATE telegram_chats SET description = 'здоровье медицина врач лечение профилактика спорт фитнес' 
WHERE LOWER(topic) = 'здоровье' AND (description IS NULL OR description = '')
AND id IN (SELECT id FROM telegram_chats WHERE LOWER(topic) = 'здоровье' AND (description IS NULL OR description = '') LIMIT 20);

-- Новости
UPDATE telegram_chats SET description = 'новости политика экономика общество происшествия' 
WHERE LOWER(topic) = 'новости' AND (description IS NULL OR description = '')
AND id IN (SELECT id FROM telegram_chats WHERE LOWER(topic) = 'новости' AND (description IS NULL OR description = '') LIMIT 20);

-- Крипто
UPDATE telegram_chats SET description = 'крипто bitcoin btc ethereum defi блокчейн трейдинг' 
WHERE LOWER(topic) = 'крипто' AND (description IS NULL OR description = '')
AND id IN (SELECT id FROM telegram_chats WHERE LOWER(topic) = 'крипто' AND (description IS NULL OR description = '') LIMIT 20);

-- Финансы
UPDATE telegram_chats SET description = 'финансы инвестиции акции облигации трейдинг банк' 
WHERE LOWER(topic) = 'финансы' AND (description IS NULL OR description = '')
AND id IN (SELECT id FROM telegram_chats WHERE LOWER(topic) = 'финансы' AND (description IS NULL OR description = '') LIMIT 20);

-- Проверяем результат
SELECT topic, COUNT(*) as count FROM telegram_chats 
WHERE is_active = true AND description IS NOT NULL AND description != '' 
GROUP BY topic ORDER BY count DESC;
