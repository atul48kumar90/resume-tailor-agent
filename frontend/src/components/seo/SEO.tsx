import { Helmet } from 'react-helmet-async';

interface SEOProps {
  title?: string;
  description?: string;
  keywords?: string;
  image?: string;
  url?: string;
  type?: string;
  noindex?: boolean;
  structuredData?: object;
  googleSiteVerification?: string; // Google Search Console verification code
}

const SEO: React.FC<SEOProps> = ({
  title = 'Resume Tailor Agent - AI-Powered Resume Optimization for ATS',
  description = 'Optimize your resume for Applicant Tracking Systems (ATS) with AI-powered resume tailoring. Get higher ATS scores, skill gap analysis, and personalized resume improvements tailored to job descriptions.',
  keywords = 'resume optimization, ATS resume, resume tailor, job application, resume builder, ATS score, resume improvement, career tools, resume analyzer',
  image = '/og-image.png',
  url = typeof window !== 'undefined' ? window.location.href : 'https://resumetailor.agent',
  type = 'website',
  noindex = false,
  structuredData,
  googleSiteVerification,
}) => {
  const fullTitle = title.includes('Resume Tailor Agent') ? title : `${title} | Resume Tailor Agent`;
  const siteUrl = typeof window !== 'undefined' ? window.location.origin : 'https://resumetailor.agent';
  const fullImageUrl = image.startsWith('http') ? image : `${siteUrl}${image}`;
  const fullUrl = url.startsWith('http') ? url : `${siteUrl}${url}`;

  return (
    <Helmet>
      {/* Primary Meta Tags */}
      <title>{fullTitle}</title>
      <meta name="title" content={fullTitle} />
      <meta name="description" content={description} />
      <meta name="keywords" content={keywords} />
      {noindex && <meta name="robots" content="noindex, nofollow" />}
      
      {/* Open Graph / Facebook */}
      <meta property="og:type" content={type} />
      <meta property="og:url" content={fullUrl} />
      <meta property="og:title" content={fullTitle} />
      <meta property="og:description" content={description} />
      <meta property="og:image" content={fullImageUrl} />
      <meta property="og:site_name" content="Resume Tailor Agent" />
      
      {/* Twitter */}
      <meta property="twitter:card" content="summary_large_image" />
      <meta property="twitter:url" content={fullUrl} />
      <meta property="twitter:title" content={fullTitle} />
      <meta property="twitter:description" content={description} />
      <meta property="twitter:image" content={fullImageUrl} />
      
      {/* Canonical URL */}
      <link rel="canonical" href={fullUrl} />
      
      {/* Google Search Console Verification */}
      {googleSiteVerification && (
        <meta name="google-site-verification" content={googleSiteVerification} />
      )}
      
      {/* Structured Data (JSON-LD) */}
      {structuredData && (
        <script type="application/ld+json">
          {JSON.stringify(structuredData)}
        </script>
      )}
    </Helmet>
  );
};

export default SEO;

