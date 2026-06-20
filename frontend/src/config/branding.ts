export const brand = {
  productName: import.meta.env.VITE_PRODUCT_NAME || 'BillionairsHQ',
  companyName: import.meta.env.VITE_COMPANY_NAME || 'Billionaires Technologies',
  docsUrl: import.meta.env.VITE_DOCS_URL || 'https://docs.billionairestechnologies.com',
  websiteUrl: import.meta.env.VITE_WEBSITE_URL || 'https://www.billionairestechnologies.com',
  repoUrl: import.meta.env.VITE_REPO_URL || 'https://github.com/billionairestechnologies/QuantX',
  xUrl: import.meta.env.VITE_X_URL || 'https://x.com/BillionairsHQ',
  youtubeUrl: import.meta.env.VITE_YOUTUBE_URL || 'https://www.youtube.com/@BillionairesTechnologies',
  discordUrl: import.meta.env.VITE_DISCORD_URL || 'https://billionairestechnologies.com/discord',
  roadmapUrl: import.meta.env.VITE_ROADMAP_URL || 'https://billionairestechnologies.com/roadmap',
}

export function brandedTitle(title?: string) {
  if (!title || title === brand.productName) {
    return brand.productName
  }
  return `${title} | ${brand.productName}`
}
