/**
 * Structured data (JSON-LD) generators for SEO
 */

export interface OrganizationSchema {
  name: string;
  url: string;
  logo?: string;
  description?: string;
}

export interface WebApplicationSchema {
  name: string;
  url: string;
  description: string;
  applicationCategory: string;
  operatingSystem: string;
  offers?: {
    price: string;
    priceCurrency: string;
  };
}

export const generateOrganizationSchema = (org: OrganizationSchema) => ({
  '@context': 'https://schema.org',
  '@type': 'Organization',
  name: org.name,
  url: org.url,
  ...(org.logo && { logo: org.logo }),
  ...(org.description && { description: org.description }),
});

export const generateWebApplicationSchema = (app: WebApplicationSchema) => ({
  '@context': 'https://schema.org',
  '@type': 'WebApplication',
  name: app.name,
  url: app.url,
  description: app.description,
  applicationCategory: app.applicationCategory,
  operatingSystem: app.operatingSystem,
  ...(app.offers && { offers: { '@type': 'Offer', ...app.offers } }),
});

export const generateBreadcrumbSchema = (items: Array<{ name: string; url: string }>) => ({
  '@context': 'https://schema.org',
  '@type': 'BreadcrumbList',
  itemListElement: items.map((item, index) => ({
    '@type': 'ListItem',
    position: index + 1,
    name: item.name,
    item: item.url,
  })),
});

export const generateSoftwareApplicationSchema = () => ({
  '@context': 'https://schema.org',
  '@type': 'SoftwareApplication',
  name: 'Resume Tailor Agent',
  applicationCategory: 'BusinessApplication',
  operatingSystem: 'Web',
  description: 'AI-powered resume optimization tool for Applicant Tracking Systems (ATS)',
  offers: {
    '@type': 'Offer',
    price: '0',
    priceCurrency: 'USD',
  },
  aggregateRating: {
    '@type': 'AggregateRating',
    ratingValue: '4.8',
    reviewCount: '150',
  },
});

export const generateFAQSchema = (faqs: Array<{ question: string; answer: string }>) => ({
  '@context': 'https://schema.org',
  '@type': 'FAQPage',
  mainEntity: faqs.map((faq) => ({
    '@type': 'Question',
    name: faq.question,
    acceptedAnswer: {
      '@type': 'Answer',
      text: faq.answer,
    },
  })),
});

