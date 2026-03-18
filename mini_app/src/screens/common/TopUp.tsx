import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ScreenShell } from '@/components/layout/ScreenShell'
import { AmountChips, Button, StepIndicator } from '@/components/ui'
import styles from './TopUp.module.css'

const CHIP_AMOUNTS = [500, 1000, 2000, 5000, 10000, 20000]

export default function TopUp() {
  const navigate = useNavigate()
  const [amount, setAmount] = useState(2000)
  const [chipSelected, setChipSelected] = useState<number | undefined>(2000)

  const handleChipSelect = (value: number) => {
    setAmount(value)
    setChipSelected(value)
  }

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const parsed = parseInt(e.target.value, 10)
    setAmount(isNaN(parsed) ? 0 : parsed)
    setChipSelected(undefined)
  }

  const isValid = amount >= 500 && amount <= 300_000

  return (
    <ScreenShell>
      <StepIndicator
        total={2}
        current={0}
        labels={['Шаг 1 — Укажите сумму пополнения', 'Шаг 2 — Подтверждение']}
      />

      <p className={styles.label}>Сколько зачислить на баланс?</p>

      <AmountChips
        amounts={CHIP_AMOUNTS}
        selected={chipSelected}
        onSelect={handleChipSelect}
      />

      <p className={styles.label}>Или введите свою сумму</p>

      <input
        type="number"
        className={styles.input}
        placeholder="от 500 ₽"
        value={amount || ''}
        onChange={handleInputChange}
      />

      <p className={styles.hint}>Мин. 500 ₽ · Макс. 300 000 ₽</p>

      <Button
        variant="primary"
        fullWidth
        disabled={!isValid}
        onClick={() => navigate('/topup/confirm', { state: { amount } })}
      >
        Продолжить →
      </Button>
    </ScreenShell>
  )
}
