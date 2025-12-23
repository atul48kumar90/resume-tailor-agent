import React from 'react';
import SEO from '../components/seo/SEO';
import { generateFAQSchema } from '../utils/structuredData';

const FAQPage: React.FC = () => {
  const faqs = [
    {
      question: 'What is Resume Tailor Agent?',
      answer: 'Resume Tailor Agent is an AI-powered tool that optimizes your resume for Applicant Tracking Systems (ATS). It analyzes your resume against job descriptions, identifies skill gaps, and provides personalized recommendations to improve your ATS score.',
    },
    {
      question: 'How does ATS optimization work?',
      answer: 'Our AI analyzes the job description to extract key skills, keywords, and requirements. It then compares your resume against these requirements, identifies missing keywords, suggests improvements, and rewrites sections to better match the job description while maintaining authenticity.',
    },
    {
      question: 'What file formats are supported?',
      answer: 'We support PDF, DOCX, and TXT formats for both resumes and job descriptions. You can upload files or paste text directly into the interface.',
    },
    {
      question: 'Is my data secure and private?',
      answer: 'Yes, we take data privacy seriously. Your resume and job descriptions are processed securely and are not shared with third parties. We use industry-standard encryption and security measures to protect your information.',
    },
    {
      question: 'How accurate is the ATS score?',
      answer: 'Our ATS scoring algorithm uses advanced keyword matching, placement analysis, experience depth, and skill proficiency detection. While we strive for accuracy, actual ATS systems may vary. Our scores provide a reliable estimate of how well your resume matches a job description.',
    },
    {
      question: 'Can I use this for multiple job applications?',
      answer: 'Absolutely! You can tailor your resume for as many job descriptions as you want. We also offer batch processing, allowing you to process multiple job descriptions at once to save time.',
    },
    {
      question: 'What is skill gap analysis?',
      answer: 'Skill gap analysis identifies which skills from the job description are missing from your resume. It categorizes skills as required, optional, or tools, helping you understand what to add or emphasize to improve your match.',
    },
    {
      question: 'Can I edit the tailored resume?',
      answer: 'Yes! After the AI tailors your resume, you can edit it directly in the preview window. You can also use our chat feature to get AI suggestions for specific sections and paste them into your resume.',
    },
    {
      question: 'How long does resume tailoring take?',
      answer: 'Typically, resume tailoring takes 30-60 seconds. The process includes analyzing the job description, parsing your resume, identifying improvements, and generating the optimized version. You can track progress in real-time.',
    },
    {
      question: 'Do I need to create an account?',
      answer: 'Currently, you can use Resume Tailor Agent without creating an account. However, creating an account allows you to save your tailored resumes, track your job applications, and access your resume history.',
    },
    {
      question: 'What makes this different from other resume builders?',
      answer: 'Resume Tailor Agent focuses specifically on ATS optimization. Unlike generic resume builders, we use AI to analyze job descriptions and tailor your resume to match specific requirements, providing skill gap analysis and ATS scoring to maximize your chances of passing through applicant tracking systems.',
    },
    {
      question: 'Can I download my tailored resume?',
      answer: 'Yes! You can download your tailored resume in PDF or DOCX format. The download includes all the optimizations made to improve your ATS score.',
    },
  ];

  const faqSchema = generateFAQSchema(faqs);

  return (
    <>
      <SEO
        title="Frequently Asked Questions - Resume Tailor Agent"
        description="Find answers to common questions about Resume Tailor Agent, ATS optimization, skill gap analysis, and how to improve your resume for job applications."
        keywords="resume FAQ, ATS optimization questions, resume tailoring help, job application tips, resume builder FAQ"
        url="/faq"
        structuredData={faqSchema}
      />
      <div className="max-w-4xl mx-auto px-4 py-12">
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">
            Frequently Asked Questions
          </h1>
          <p className="text-xl text-gray-600">
            Everything you need to know about Resume Tailor Agent
          </p>
        </div>

        <div className="space-y-6">
          {faqs.map((faq, index) => (
            <div
              key={index}
              className="bg-white rounded-lg shadow-md p-6 border border-gray-200"
            >
              <h2 className="text-xl font-semibold text-gray-900 mb-3 flex items-start">
                <span className="text-blue-600 mr-3 mt-1">Q{index + 1}.</span>
                <span>{faq.question}</span>
              </h2>
              <div className="ml-8 text-gray-700 leading-relaxed">
                <p>{faq.answer}</p>
              </div>
            </div>
          ))}
        </div>

        <div className="mt-12 bg-blue-50 border border-blue-200 rounded-lg p-6">
          <h3 className="text-xl font-semibold text-gray-900 mb-3">
            Still have questions?
          </h3>
          <p className="text-gray-700 mb-4">
            If you couldn't find the answer you're looking for, feel free to reach out to our support team.
          </p>
          <a
            href="mailto:support@resumetailor.agent"
            className="inline-block bg-blue-600 text-white px-6 py-2 rounded-md font-medium hover:bg-blue-700 transition-colors"
          >
            Contact Support
          </a>
        </div>
      </div>
    </>
  );
};

export default FAQPage;

