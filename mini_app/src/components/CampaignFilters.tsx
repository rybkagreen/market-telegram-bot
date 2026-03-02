import React, { useState } from 'react';
import './CampaignFilters.css';

export interface CampaignFilters {
  topics: string[];
  min_members: number;
  max_members: number;
  blacklist: number[];
}

interface CampaignFiltersProps {
  filters: CampaignFilters;
  onChange: (filters: CampaignFilters) => void;
}

const AVAILABLE_TOPICS = [
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

export const CampaignFilters: React.FC<CampaignFiltersProps> = ({
  filters,
  onChange,
}) => {
  const [selectedTopics, setSelectedTopics] = useState<string[]>(filters.topics || []);
  const [minMembers, setMinMembers] = useState<number>(filters.min_members || 0);
  const [maxMembers, setMaxMembers] = useState<number>(filters.max_members || 1000000);

  const handleTopicToggle = (topic: string) => {
    const newTopics = selectedTopics.includes(topic)
      ? selectedTopics.filter((t) => t !== topic)
      : [...selectedTopics, topic];
    
    setSelectedTopics(newTopics);
    onChange({
      ...filters,
      topics: newTopics,
      min_members: minMembers,
      max_members: maxMembers,
      blacklist: filters.blacklist || [],
    });
  };

  const handleMinMembersChange = (value: number) => {
    setMinMembers(value);
    onChange({
      ...filters,
      topics: selectedTopics,
      min_members: value,
      max_members: maxMembers,
      blacklist: filters.blacklist || [],
    });
  };

  const handleMaxMembersChange = (value: number) => {
    setMaxMembers(value);
    onChange({
      ...filters,
      topics: selectedTopics,
      min_members: minMembers,
      max_members: value,
      blacklist: filters.blacklist || [],
    });
  };

  const handleClearFilters = () => {
    setSelectedTopics([]);
    setMinMembers(0);
    setMaxMembers(1000000);
    onChange({
      topics: [],
      min_members: 0,
      max_members: 1000000,
      blacklist: [],
    });
  };

  return (
    <div className="campaign-filters">
      <div className="filters-header">
        <h3>🎯 Таргетинг</h3>
        <button className="clear-btn" onClick={handleClearFilters}>
          Сбросить
        </button>
      </div>

      {/* Тематики */}
      <div className="filter-section">
        <label className="filter-label">Тематики</label>
        <div className="topics-grid">
          {AVAILABLE_TOPICS.map((topic) => (
            <button
              key={topic}
              className={`topic-chip ${selectedTopics.includes(topic) ? 'selected' : ''}`}
              onClick={() => handleTopicToggle(topic)}
            >
              {topic}
            </button>
          ))}
        </div>
      </div>

      {/* Размер чатов */}
      <div className="filter-section">
        <label className="filter-label">Размер чатов</label>
        <div className="range-inputs">
          <div className="input-group">
            <label>От</label>
            <input
              type="number"
              value={minMembers || ''}
              onChange={(e) => handleMinMembersChange(Number(e.target.value))}
              placeholder="0"
              min="0"
            />
          </div>
          <span className="separator">—</span>
          <div className="input-group">
            <label>До</label>
            <input
              type="number"
              value={maxMembers === 1000000 ? '' : maxMembers}
              onChange={(e) => handleMaxMembersChange(Number(e.target.value) || 1000000)}
              placeholder="1 000 000"
              min="0"
            />
          </div>
        </div>
      </div>

      {/* Пресеты */}
      <div className="filter-section">
        <label className="filter-label">Быстрые пресеты</label>
        <div className="presets">
          <button
            className="preset-chip"
            onClick={() => {
              handleMinMembersChange(0);
              handleMaxMembersChange(1000000);
            }}
          >
            Все размеры
          </button>
          <button
            className="preset-chip"
            onClick={() => {
              handleMinMembersChange(100);
              handleMaxMembersChange(1000);
            }}
          >
            Малые (100-1K)
          </button>
          <button
            className="preset-chip"
            onClick={() => {
              handleMinMembersChange(1000);
              handleMaxMembersChange(10000);
            }}
          >
            Средние (1K-10K)
          </button>
          <button
            className="preset-chip"
            onClick={() => {
              handleMinMembersChange(10000);
              handleMaxMembersChange(1000000);
            }}
          >
            Крупные (10K+)
          </button>
        </div>
      </div>

      {/* Инфо */}
      <div className="filter-info">
        <p>
          💡 Выберите тематики и размер чатов для таргетированной рассылки.
          Это повысит конверсию и снизит стоимость.
        </p>
      </div>
    </div>
  );
};
