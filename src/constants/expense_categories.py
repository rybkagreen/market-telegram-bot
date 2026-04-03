"""Expense categories per ст. 346.16 НК РФ for ООО УСН 15% (доходы − расходы)."""

from enum import Enum


class ExpenseCategory(str, Enum):
    """Классификатор расходов для налоговой базы УСН 15%.

    Категории соответствуют перечню расходов в ст. 346.16 НК РФ.
    """

    # Выплаты владельцам каналов (подрядчикам) за размещение рекламы
    PAYOUT_TO_CONTRACTORS = "payout_to_contractors"
    # Банковские комиссии: ЮKassa, комиссии за вывод средств
    BANK_COMMISSIONS = "bank_commissions"
    # ПО, хостинг, домен, серверы
    SOFTWARE_HOSTING = "software_hosting"
    # Налоги, пошлины, сборы (НДФЛ, НДС, минимальный налог)
    TAXES_AND_FEES = "taxes_and_fees"
    # Прочие расходы, не вошедшие в категории
    OTHER = "other"
