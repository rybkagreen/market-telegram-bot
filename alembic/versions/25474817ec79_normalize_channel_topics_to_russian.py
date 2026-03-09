"""normalize_channel_topics_to_russian

Revision ID: 25474817ec79
Revises: 8885dc6d508e
Create Date: 2026-03-10

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "25474817ec79"
down_revision: str | None = "8885dc6d508e"
branch_labels: str | list[str] | None = None
depends_on: str | list[str] | None = None


def upgrade() -> None:
    """Нормализация названий тем на русский язык."""
    
    # business → бизнес
    op.execute("""
        UPDATE telegram_chats 
        SET topic = 'бизнес' 
        WHERE topic = 'business'
    """)
    
    # education → образование
    op.execute("""
        UPDATE telegram_chats 
        SET topic = 'образование' 
        WHERE topic = 'education'
    """)
    
    # marketing → маркетинг
    op.execute("""
        UPDATE telegram_chats 
        SET topic = 'маркетинг' 
        WHERE topic = 'marketing'
    """)
    
    # news → новости
    op.execute("""
        UPDATE telegram_chats 
        SET topic = 'новости' 
        WHERE topic = 'news'
    """)
    
    # health → здоровье
    op.execute("""
        UPDATE telegram_chats 
        SET topic = 'здоровье' 
        WHERE topic = 'health'
    """)
    
    # finance → финансы
    op.execute("""
        UPDATE telegram_chats 
        SET topic = 'финансы' 
        WHERE topic = 'finance'
    """)
    
    # crypto → крипто
    op.execute("""
        UPDATE telegram_chats 
        SET topic = 'крипто' 
        WHERE topic = 'crypto'
    """)
    
    # other → другое
    op.execute("""
        UPDATE telegram_chats 
        SET topic = 'другое' 
        WHERE topic = 'other'
    """)


def downgrade() -> None:
    """Откат нормализации (возврат к английским названиям)."""
    
    op.execute("""
        UPDATE telegram_chats 
        SET topic = 'business' 
        WHERE topic = 'бизнес'
    """)
    
    op.execute("""
        UPDATE telegram_chats 
        SET topic = 'education' 
        WHERE topic = 'образование'
    """)
    
    op.execute("""
        UPDATE telegram_chats 
        SET topic = 'marketing' 
        WHERE topic = 'маркетинг'
    """)
    
    op.execute("""
        UPDATE telegram_chats 
        SET topic = 'news' 
        WHERE topic = 'новости'
    """)
    
    op.execute("""
        UPDATE telegram_chats 
        SET topic = 'health' 
        WHERE topic = 'здоровье'
    """)
    
    op.execute("""
        UPDATE telegram_chats 
        SET topic = 'finance' 
        WHERE topic = 'финансы'
    """)
    
    op.execute("""
        UPDATE telegram_chats 
        SET topic = 'crypto' 
        WHERE topic = 'крипто'
    """)
    
    op.execute("""
        UPDATE telegram_chats 
        SET topic = 'other' 
        WHERE topic = 'другое'
    """)
