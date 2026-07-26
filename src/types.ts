export type AnswerKey = 'A' | 'B' | 'C' | 'D'

export interface ManualRef {
  chapter: number
  section: string
  sectionTitle: string
  label: string
  path: string
  confidence?: 'high' | 'medium' | 'low'
  paragraph?: string
}

export interface Question {
  id: string
  number: number
  bankId: string | null
  chapter: number | null
  subchapter: number | null
  section: string | null
  stem: string
  options: Partial<Record<AnswerKey, string>>
  answer: AnswerKey
  explanation: string
  hot: boolean
  chapterTitle: string
  sourcePage?: number
  image?: string | null
  /** Link to study-manual section that supports this answer. */
  manualRef?: ManualRef
}

export interface QuestionBank {
  source: string
  extractedAt: string
  total: number
  chapters: Record<string, string>
  questions: Question[]
}

export interface ExamConfig {
  totalQuestions: number
  durationMinutes: number
  passPercent: number
  /** Target count per chapter (1–9). */
  chapterCounts: Record<number, number>
}

export interface ExamQuestion extends Question {
  examIndex: number
}

export interface ExamResult {
  score: number
  total: number
  percent: number
  passed: boolean
  answers: Record<string, AnswerKey | null>
  questions: ExamQuestion[]
  durationSeconds: number
}
