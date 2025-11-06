'use client';

import { useState } from 'react';
import { 
  BookOpen, 
  ExternalLink, 
  HelpCircle, 
  Video, 
  FileText, 
  MessageCircle,
  ChevronRight,
  Search
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';

interface HelpResource {
  id: string;
  title: string;
  description: string;
  type: 'guide' | 'video' | 'faq' | 'external';
  url: string;
  category: 'setup' | 'troubleshooting' | 'advanced' | 'general';
  estimatedTime?: string;
  difficulty?: 'beginner' | 'intermediate' | 'advanced';
}

interface FAQItem {
  question: string;
  answer: string;
  category: string;
}

const helpResources: HelpResource[] = [
  {
    id: 'setup-guide',
    title: 'Complete Setup Guide',
    description: 'Step-by-step guide with screenshots for AWS account setup',
    type: 'guide',
    url: '/docs/setup-guide',
    category: 'setup',
    estimatedTime: '10 min',
    difficulty: 'beginner'
  },
  {
    id: 'video-tutorial',
    title: 'Video Walkthrough',
    description: 'Watch a complete setup demonstration',
    type: 'video',
    url: '/docs/video-tutorial',
    category: 'setup',
    estimatedTime: '8 min',
    difficulty: 'beginner'
  },
  {
    id: 'iam-permissions',
    title: 'IAM Permissions Guide',
    description: 'Detailed explanation of required AWS permissions',
    type: 'guide',
    url: '/docs/iam-permissions',
    category: 'setup',
    estimatedTime: '5 min',
    difficulty: 'intermediate'
  },
  {
    id: 'troubleshooting',
    title: 'Troubleshooting Common Issues',
    description: 'Solutions for the most common setup problems',
    type: 'guide',
    url: '/docs/troubleshooting',
    category: 'troubleshooting',
    estimatedTime: '3 min',
    difficulty: 'beginner'
  },
  {
    id: 'aws-docs-iam',
    title: 'AWS IAM Documentation',
    description: 'Official AWS guide on IAM roles and policies',
    type: 'external',
    url: 'https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles.html',
    category: 'setup',
    difficulty: 'intermediate'
  },
  {
    id: 'aws-cost-explorer',
    title: 'AWS Cost Explorer API',
    description: 'AWS documentation for Cost Explorer permissions',
    type: 'external',
    url: 'https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/ce-api.html',
    category: 'advanced',
    difficulty: 'advanced'
  }
];

const faqItems: FAQItem[] = [
  {
    question: "What permissions does CostsHub need?",
    answer: "CostsHub requires read-only access to your AWS Cost Explorer data, billing information, and organization details. We never need write permissions or access to your actual resources.",
    category: "setup"
  },
  {
    question: "How long does it take to see cost data?",
    answer: "Initial data sync typically takes 5-15 minutes. Historical data (up to 12 months) will be available within 1 hour. Real-time updates occur every 6 hours.",
    category: "setup"
  },
  {
    question: "Is my cost data secure?",
    answer: "Yes, all data is encrypted in transit and at rest. We use AWS security best practices and never store sensitive account credentials. Only aggregated cost data is processed.",
    category: "general"
  },
  {
    question: "Can I connect multiple AWS accounts?",
    answer: "Yes, you can connect multiple AWS accounts to get a consolidated view of your costs across all accounts and organizations.",
    category: "setup"
  },
  {
    question: "What if my connection test fails?",
    answer: "Common causes include incorrect IAM role ARN, missing permissions, or incorrect External ID. Check our troubleshooting guide for step-by-step solutions.",
    category: "troubleshooting"
  },
  {
    question: "How do I find my AWS Account ID?",
    answer: "Your AWS Account ID is displayed in the top-right corner of the AWS Console. It's a 12-digit number. You can also find it in the IAM dashboard.",
    category: "setup"
  }
];

export function HelpDocumentation() {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory] = useState<string>('all');

  const filteredResources = helpResources.filter(resource => {
    const matchesSearch = resource.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         resource.description.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesCategory = selectedCategory === 'all' || resource.category === selectedCategory;
    return matchesSearch && matchesCategory;
  });

  const filteredFAQs = faqItems.filter(faq => {
    const matchesSearch = faq.question.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         faq.answer.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesCategory = selectedCategory === 'all' || faq.category === selectedCategory;
    return matchesSearch && matchesCategory;
  });

  const getResourceIcon = (type: HelpResource['type']) => {
    switch (type) {
      case 'video':
        return <Video className="h-4 w-4" />;
      case 'external':
        return <ExternalLink className="h-4 w-4" />;
      case 'faq':
        return <HelpCircle className="h-4 w-4" />;
      default:
        return <FileText className="h-4 w-4" />;
    }
  };

  const getDifficultyBadge = (difficulty?: HelpResource['difficulty']) => {
    if (!difficulty) return null;
    
    const colors = {
      beginner: 'bg-green-100 text-green-800',
      intermediate: 'bg-yellow-100 text-yellow-800',
      advanced: 'bg-red-100 text-red-800'
    };

    return (
      <Badge variant="secondary" className={colors[difficulty]}>
        {difficulty}
      </Badge>
    );
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center">
          <BookOpen className="h-5 w-5 mr-2" />
          Help & Documentation
        </CardTitle>
        <div className="space-y-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
            <Input
              placeholder="Search help articles..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10"
            />
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="guides" className="w-full">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="guides">Guides</TabsTrigger>
            <TabsTrigger value="faq">FAQ</TabsTrigger>
            <TabsTrigger value="support">Support</TabsTrigger>
          </TabsList>

          <TabsContent value="guides" className="space-y-4">
            <div className="space-y-3">
              {filteredResources.map((resource) => (
                <div key={resource.id} className="border rounded-lg p-4 hover:bg-gray-50 transition-colors">
                  <div className="flex items-start justify-between">
                    <div className="flex items-start space-x-3 flex-1">
                      <div className="flex-shrink-0 mt-1">
                        {getResourceIcon(resource.type)}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center space-x-2 mb-1">
                          <h4 className="font-medium text-gray-900">{resource.title}</h4>
                          {getDifficultyBadge(resource.difficulty)}
                          {resource.estimatedTime && (
                            <Badge variant="outline" className="text-xs">
                              {resource.estimatedTime}
                            </Badge>
                          )}
                        </div>
                        <p className="text-sm text-gray-600">{resource.description}</p>
                      </div>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => window.open(resource.url, resource.type === 'external' ? '_blank' : '_self')}
                    >
                      <ChevronRight className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </TabsContent>

          <TabsContent value="faq" className="space-y-4">
            <div className="space-y-2">
              {filteredFAQs.map((faq, index) => (
                <Collapsible key={index}>
                  <CollapsibleTrigger asChild>
                    <Button variant="ghost" className="w-full justify-between p-4 h-auto text-left">
                      <span className="font-medium">{faq.question}</span>
                      <ChevronRight className="h-4 w-4 flex-shrink-0" />
                    </Button>
                  </CollapsibleTrigger>
                  <CollapsibleContent className="px-4 pb-4">
                    <p className="text-sm text-gray-600">{faq.answer}</p>
                  </CollapsibleContent>
                </Collapsible>
              ))}
            </div>
          </TabsContent>

          <TabsContent value="support" className="space-y-4">
            <div className="space-y-4">
              <div className="text-center p-6 border rounded-lg">
                <MessageCircle className="h-12 w-12 text-blue-500 mx-auto mb-4" />
                <h3 className="font-semibold text-gray-900 mb-2">Need More Help?</h3>
                <p className="text-sm text-gray-600 mb-4">
                  Can't find what you're looking for? Our support team is here to help.
                </p>
                <div className="space-y-2">
                  <Button className="w-full">
                    <MessageCircle className="h-4 w-4 mr-2" />
                    Contact Support
                  </Button>
                  <Button variant="outline" className="w-full">
                    <BookOpen className="h-4 w-4 mr-2" />
                    Schedule Demo
                  </Button>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="border rounded-lg p-4">
                  <h4 className="font-medium mb-2">Email Support</h4>
                  <p className="text-sm text-gray-600 mb-3">
                    Get help via email within 24 hours
                  </p>
                  <Button variant="outline" size="sm">
                    support@costshub.com
                  </Button>
                </div>
                <div className="border rounded-lg p-4">
                  <h4 className="font-medium mb-2">Live Chat</h4>
                  <p className="text-sm text-gray-600 mb-3">
                    Chat with our team during business hours
                  </p>
                  <Button variant="outline" size="sm">
                    Start Chat
                  </Button>
                </div>
              </div>
            </div>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}