export interface ManualBlockBase {
  type: string
}

export interface ManualParagraphBlock extends ManualBlockBase {
  type: 'p'
  text: string
  /** Paragraph number badge, e.g. "1.1" */
  num?: string
}

export interface ManualListBlock extends ManualBlockBase {
  type: 'li'
  text: string
}

export interface ManualHeadingBlock extends ManualBlockBase {
  type: 'h3'
  text: string
}

export interface ManualFigureBlock extends ManualBlockBase {
  type: 'figure'
  caption: string
  figureId?: string
  kind?: 'figure' | 'table'
  src?: string
  alt?: string
}

export type ManualBlock =
  | ManualParagraphBlock
  | ManualListBlock
  | ManualHeadingBlock
  | ManualFigureBlock

export interface ManualSection {
  id: string
  title: string
  blocks: ManualBlock[]
}

export interface ManualNavItem {
  id: string
  title: string
  available?: boolean
}

export interface ManualFigureMeta {
  src: string
  alt?: string
  caption?: string
  pdfPage?: number
  chapter?: number
  figureNum?: string
  kind?: 'figure' | 'table'
}

export interface ManualChapter {
  id: string
  number: number
  title: string
  fullTitle: string
  pdfPageStart?: number
  pdfPageEnd?: number
  nav: ManualNavItem[]
  sections: ManualSection[]
  figures?: ManualFigureMeta[]
}

export interface ManualChapterSummary {
  id: string
  number: number
  title: string
  fullTitle: string
  sectionCount: number
  nav: ManualNavItem[]
  file: string
}

export interface ManualMeta {
  versionId: string
  edition: string
  versionLabel: string
  versionFull: string
  firstPublished: string
  firstPublishedLabel: string
  updatedThrough: string
  updatedThroughLabel: string
  publisher: string
  paper: string
  isbn?: string
  sourceFile?: string
  notes?: string[]
  chapterCount: number
  chapters: ManualChapterSummary[]
  extras?: { id: string; title: string; file: string }[]
}

export interface ManualIndex {
  currentVersion: string
  availableVersions: {
    versionId: string
    versionLabel: string
    updatedThrough: string
    updatedThroughLabel: string
    edition: string
    path: string
  }[]
  howToUpdate?: string[]
}

export interface ManualExtra {
  title: string
  updatedAt?: string
  updatedAtLabel?: string
  text: string
}
