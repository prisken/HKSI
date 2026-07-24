import type { AnswerKey, ExamConfig, ExamQuestion, Question } from '../types'

/** Study manual: 60 MCQs, 90 minutes, 70% pass. Chapter counts follow commonly cited Paper 1 weightings. */
export const EXAM_CONFIG: ExamConfig = {
  totalQuestions: 60,
  durationMinutes: 90,
  passPercent: 70,
  chapterCounts: {
    1: 4,
    2: 4,
    3: 7,
    4: 13,
    5: 10,
    6: 9,
    7: 5,
    8: 3,
    9: 5,
  },
}

export const CHAPTER_TITLES: Record<number, string> = {
  1: '香港金融業監管概覽',
  2: '相關香港法例及新《公司條例》的原則',
  3: '《證券及期貨條例》',
  4: '發牌及註冊與附屬法例',
  5: '業務操守與客戶關係',
  6: '業務運作與常規',
  7: '在香港交易所的參與',
  8: '企業融資及證監會的認可產品',
  9: '市場失當行為及不當交易行為',
}

export function shuffle<T>(items: T[], rng = Math.random): T[] {
  const arr = [...items]
  for (let i = arr.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1))
    ;[arr[i], arr[j]] = [arr[j], arr[i]]
  }
  return arr
}

/**
 * Build a mock exam by sampling questions using the chapter ratio from EXAM_CONFIG.
 * If a chapter lacks enough items, remaining slots are filled from other chapters.
 */
export function buildExamPaper(bank: Question[], config: ExamConfig = EXAM_CONFIG): ExamQuestion[] {
  const byChapter = new Map<number, Question[]>()
  for (const q of bank) {
    if (!q.chapter || !q.answer) continue
    const list = byChapter.get(q.chapter) ?? []
    list.push(q)
    byChapter.set(q.chapter, list)
  }

  const picked: Question[] = []
  const used = new Set<string>()
  const shortfall: number[] = []

  for (const chapter of Object.keys(config.chapterCounts).map(Number)) {
    const target = config.chapterCounts[chapter]
    const pool = shuffle(byChapter.get(chapter) ?? [])
    const take = Math.min(target, pool.length)
    for (let i = 0; i < take; i++) {
      picked.push(pool[i])
      used.add(pool[i].id)
    }
    if (take < target) shortfall.push(target - take)
  }

  let need = shortfall.reduce((a, b) => a + b, 0)
  need += Math.max(0, config.totalQuestions - picked.length)

  if (need > 0) {
    const filler = shuffle(bank.filter((q) => q.answer && !used.has(q.id)))
    for (const q of filler) {
      if (need <= 0) break
      picked.push(q)
      used.add(q.id)
      need--
    }
  }

  const paper = shuffle(picked).slice(0, config.totalQuestions)
  return paper.map((q, examIndex) => ({ ...q, examIndex }))
}

export function scoreExam(
  questions: ExamQuestion[],
  answers: Record<string, AnswerKey | null>,
): { score: number; percent: number; passed: boolean } {
  let score = 0
  for (const q of questions) {
    if (answers[q.id] && answers[q.id] === q.answer) score++
  }
  const percent = questions.length ? Math.round((score / questions.length) * 1000) / 10 : 0
  const passed = percent >= EXAM_CONFIG.passPercent
  return { score, percent, passed }
}

export function groupByChapter(questions: Question[]): { chapter: number; title: string; questions: Question[] }[] {
  const map = new Map<number, Question[]>()
  for (const q of questions) {
    const ch = q.chapter ?? 0
    const list = map.get(ch) ?? []
    list.push(q)
    map.set(ch, list)
  }
  return [...map.entries()]
    .sort((a, b) => a[0] - b[0])
    .map(([chapter, qs]) => ({
      chapter,
      title: CHAPTER_TITLES[chapter] ?? (chapter === 0 ? '未分類' : `第 ${chapter} 章`),
      questions: qs.sort((a, b) => a.number - b.number),
    }))
}

export function formatTime(totalSeconds: number): string {
  const s = Math.max(0, Math.floor(totalSeconds))
  const m = Math.floor(s / 60)
  const r = s % 60
  return `${String(m).padStart(2, '0')}:${String(r).padStart(2, '0')}`
}
