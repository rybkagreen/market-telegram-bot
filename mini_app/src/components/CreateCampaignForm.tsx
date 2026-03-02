import React, { useState } from 'react';
import { CampaignFilters, CampaignFilters as FiltersType } from './CampaignFilters';
import { campaignsApi, CreateCampaignDTO } from '../api/campaigns';
import './CreateCampaignForm.css';

interface CreateCampaignFormProps {
  onSuccess: (campaignId: number) => void;
  onCancel: () => void;
}

export const CreateCampaignForm: React.FC<CreateCampaignFormProps> = ({
  onSuccess,
  onCancel,
}) => {
  const [title, setTitle] = useState('');
  const [text, setText] = useState('');
  const [topic, setTopic] = useState('');
  const [filters, setFilters] = useState<FiltersType>({
    topics: [],
    min_members: 0,
    max_members: 1000000,
    blacklist: [],
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const data: CreateCampaignDTO = {
        title,
        text,
        topic: topic || undefined,
        filters: {
          topics: filters.topics.length > 0 ? filters.topics : undefined,
          min_members: filters.min_members,
          max_members: filters.max_members,
          blacklist: filters.blacklist,
        },
      };

      const result = await campaignsApi.create(data);
      onSuccess(result.id);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Ошибка при создании кампании');
      setLoading(false);
    }
  };

  const topics = [
    'бизнес',
    'маркетинг',
    'it',
    'финансы',
    'крипта',
    'инвестиции',
    'недвижимость',
    'авто',
    'путешествия',
    'еда',
    'мода',
    'здоровье',
    'спорт',
    'образование',
    'новости',
    'развлечения',
  ];

  return (
    <form className="create-campaign-form" onSubmit={handleSubmit}>
      <div className="form-header">
        <h2>🚀 Новая кампания</h2>
        <button type="button" className="close-btn" onClick={onCancel}>
          ✕
        </button>
      </div>

      {error && <div className="error-message">{error}</div>}

      <div className="form-group">
        <label htmlFor="title">Название</label>
        <input
          id="title"
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Например: Реклама курса по маркетингу"
          required
        />
      </div>

      <div className="form-group">
        <label htmlFor="topic">Тематика кампании</label>
        <select
          id="topic"
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
        >
          <option value="">Не указано</option>
          {topics.map((t) => (
            <option key={t} value={t}>{t}</option>
          ))}
        </select>
      </div>

      <div className="form-group">
        <label htmlFor="text">Текст сообщения</label>
        <textarea
          id="text"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Введите текст рекламного сообщения..."
          rows={6}
          required
        />
        <div className="char-count">{text.length} символов</div>
      </div>

      <div className="form-group">
        <CampaignFilters filters={filters} onChange={setFilters} />
      </div>

      <div className="form-actions">
        <button type="button" className="btn-secondary" onClick={onCancel}>
          Отмена
        </button>
        <button type="submit" className="btn-primary" disabled={loading}>
          {loading ? 'Создание...' : 'Создать кампанию'}
        </button>
      </div>
    </form>
  );
};
